"""runner — läuft einen Prototypen über die Orakel und misst die Delta.

Der Runner ist bewusst klein und generisch. Er kennt nur die
gw_shared_lib-Primitive (RAGPipeline, analyse, GuardPipeline) und die
Manifest-Form. Ein neuer Prototyp bringt kein eigenes Runner-Modul mit;
er bringt einfach ein Manifest + einen pipeline.py-Modul (für Non-RAG-
Domänen wie E-Mail-Triage).
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union

# Ensure vendor/ is importable when run from anywhere.
_VEN = Path(__file__).resolve().parents[1] / "vendor"
if _VEN.exists() and str(_VEN) not in sys.path:
    sys.path.insert(0, str(_VEN))

from gw_shared_lib import (      # noqa: E402
    RAGPipeline,
    GuardPipeline,
    StubClient,
    analyse,
    audit_action,
)
from gw_shared_lib.inference import Client   # noqa: E402

from .manifest import Manifest, Case


@dataclass
class OracleRun:
    oracle: str
    available: bool = True
    notes: str = ""
    results: dict[str, dict] = field(default_factory=dict)

    @property
    def info_ok(self) -> int:
        n = 0
        for r in self.results.values():
            if r.get("case_expect") == "info" and r.get("hit"):
                n += 1
        return n

    def metric_recall_at_k(self, golden_source_prefix: Optional[str] = None) -> float:
        info = [r for r in self.results.values() if r.get("case_expect") == "info"]
        if not info:
            return 0.0
        hits = sum(1 for r in info if r.get("hit"))
        return hits / len(info)

    def metric_guard_blocks(self) -> float:
        """Fraktion der guard_block-Cases, beim denen tatsächlich blockiert wurde."""
        gb = [r for r in self.results.values() if r.get("case_expect") == "guard_block"]
        if not gb:
            return 1.0
        return float(sum(1 for r in gb if r.get("hit"))) / len(gb)

    def metric_for(self, name: str) -> float:
        known = {
            "recall@3": self.metric_recall_at_k,
            "guard_blocks": self.metric_guard_blocks,
        }
        if name not in known:
            raise KeyError(f"unknown metric: {name}")
        return known[name]()

    def delta_vs(self, other: "OracleRun", name: str) -> float:
        return self.metric_for(name) - other.metric_for(name)


@dataclass
class GateMetrics:
    demo: OracleRun
    prod: OracleRun
    prod_available: bool = False


def load_pipeline(manifest: Manifest, root: Path) -> Callable:
    """Ein optionales pipeline.py pro Prototyp für Non-RAG-Domänen.

    Konvention: `prototypes/<id>/pipeline.py` mit
    `def run(case, oracle) -> dict` (ergibt einen Result-Dict, identisch
    zum RAG-Format). Fehlt nicht -> Standard-RAG.
    """
    pkg = root / "prototypes" / manifest.id / "pipeline.py"
    if not pkg.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        f"gw_proto_pipeline_{manifest.id}", pkg
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, "spec_from_file_location returned None"
    spec.loader.exec_module(module)
    return module.run


def run_rag_case(
    manifest: Manifest,
    case: Case,
    *,
    oracle_url: str,
    oracle_embed: str,
    use_stub: bool,
    min_score: float,
    guard: bool,
) -> dict:
    """Ein RAG-Fall: Guard → Retrieval → Antwort → Assertion.

    Rückgabe-Shape (identisch über alle Orakel, damit DELTAs Sinn
    ergeben):
      {case_expect, blocked, blocked_reason, hit, cites, top_source,
       top_score, note}
    """
    from gw_shared_lib import Chunk as _C
    corpus = [
        _C(content=c["content"], source=c.get("source", ""),
           confidence=float(c.get("confidence", 0.5)),
           access_level=c.get("access_level", "public"))
        for c in manifest.corpus
    ]
    pipe = RAGPipeline(
        corpus=corpus,
        guard=GuardPipeline() if guard else None,
        top_k=3,
        min_score=min_score,
        ollama_url=oracle_url,
        embed_model=oracle_embed,
        use_stub=use_stub,
    )

    res = pipe.answer(case.question)
    out = {
        "case_expect": case.expect,
        "blocked": bool(res.guard_blocked),
        "blocked_reason": res.guard_reason or "",
        "hit": bool(res.citations),
        "cites": res.citations[:3],
        "top_source": (res.citations[0]["source"] if res.citations else ""),
        "top_score": float(res.confidence or 0.0),
    }
    if case.expect == "guard_block":
        out["hit"] = bool(res.guard_blocked)
    elif case.expect == "no_answer":
        out["hit"] = not bool(res.citations)   # "no info" is the success
    elif case.expect == "info":
        # a golden source must appear in the top citations
        if res.citations and case.golden:
            out["hit"] = any(case.golden in (c.get("source", "") or "") for c in res.citations[:3])
        else:
            out["hit"] = bool(res.citations)
    return out


def run_case(
    manifest: Manifest,
    case: Case,
    oracle_spec,
    *,
    min_score: float,
    pipeline_fn: Optional[Callable] = None,
) -> dict:
    """Läuft einen Case durch ein Orakel.

    Wenn ein pipeline.py den Fall übernimmt (Non-RAG), rufe es auf;
    andernfalls der generische RAG-Pfad.
    """
    use_stub = oracle_spec.client == "stub"
    if pipeline_fn is not None:
        return pipeline_fn(case, oracle_spec, use_stub=use_stub, manifest=manifest)
    return run_rag_case(
        manifest, case,
        oracle_url=oracle_spec.url,
        oracle_embed=oracle_spec.embed_model,
        use_stub=use_stub,
        min_score=min_score,
        guard=manifest.guard,
    )


def probe_client(oracle_spec, *, warmup: int = 3) -> bool:
    """Prüft, ob ein PROD-Orakel (echtes Modell) erreichbar ist.

    Fail-soft: ein fehlgeschlagener Probe -> False (nicht "crash").
    Ollama lädt das Embedding-Modell erst auf Abfrage (cold-start);
    bis es warm ist, kommen leere Vektoren. Deshalb ein paar
    Warm-up-Versuche mit kleiner Pause.
    """
    if oracle_spec.client in ("stub",):
        return True
    client = Client(url=oracle_spec.url, embed_model=oracle_spec.embed_model)
    for i in range(warmup):
        try:
            out = client.embed("probe")
            vec = out[0] if isinstance(out, list) and out and isinstance(out[0], list) else out
            if vec and isinstance(vec, list) and len(vec) > 0:
                return True
            import time
            time.sleep(1.0)      # cold-start: Model lädt gerade
        except Exception:
            import time
            time.sleep(1.0)
    return False


def run_manifest(manifest: Manifest, *, root: Path, audit_path: Optional[Path] = None,
                 probe: bool = True) -> GateMetrics:
    """Läuft alle Cases über DEMO und PROD (falls verfügbar)."""
    import sys as _s
    if str(root) not in _s.path:
        _s.path.insert(0, str(root))
    pipeline_fn = load_pipeline(manifest, root)

    demo_spec = manifest.oracles.get("demo") or manifest.oracles.get("prod")
    prod_spec = manifest.oracles.get("prod")
    prod_available = probe and probe_client(prod_spec) if prod_spec.client != "stub" else True

    demo_out = OracleRun(oracle="demo")
    prod_out = OracleRun(oracle="prod")

    for c in manifest.cases:
        demo_out.results[c.id] = run_case(
            manifest, c, demo_spec, min_score=manifest.min_score_demo,
            pipeline_fn=pipeline_fn)
        if prod_available:
            prod_out.results[c.id] = run_case(
                manifest, c, prod_spec, min_score=manifest.min_score_prod,
                pipeline_fn=pipeline_fn)
        else:
            prod_out.results[c.id] = {
                "case_expect": c.expect, "blocked": False, "blocked_reason": "",
                "hit": None, "cites": [], "top_source": "", "top_score": 0.0,
                "note": "prod oracle unavailable",
            }

    demo_out.available = True
    prod_out.available = prod_available

    if audit_path:
        for c in manifest.cases:
            for label, r in (("demo", demo_out.results[c.id]),
                             ("prod", prod_out.results[c.id] if prod_available else None)):
                if r is None:
                    continue
                audit_action(str(audit_path),
                             action="proto_case",
                             actor=f"gate:{manifest.id}",
                             input=c.question[:120],
                             category="prototype-gate",
                             fall_id=c.id,
                             source=r.get("top_source", ""),
                             confidence=r.get("top_score", 0.0),
                             data={"oracle": label, "result": r},
                             )

    return GateMetrics(demo=demo_out, prod=prod_out, prod_available=prod_available)
