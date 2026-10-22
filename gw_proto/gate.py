"""gate — das Verdict: GO / NO-GO + der sichtbare Demo-vs-Prod-Delta.

Das ist das Herzstück "wann erfolgreich / wann nicht":
  - Per Kriterium in manifest.production_criteria wird ein GO/FAIL gezogen.
  - PRODUCTION-GO zählt ZÄHLEN, wo PROD das Kriterium erfüllt.
  - Ist kein PROD-Orakel da, ist das PROD-Kriterium "pending" und
    das Gesamt-Verdict wird "CONDITIONAL" (nicht GO) — der reale
    Zustand, nicht ein vorgetäuschtes "erfolgreich".
  - Der DELTA (PROD - DEMO) wird pro Metrik sichtbar: er zeigt, wie viel
    ein echtes Modell dem Offline-Demo bringt (oder nichts bringt).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .manifest import Manifest, Criterion
from .runner import GateMetrics


_OP = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: abs(a - b) < 1e-9,
    "!=": lambda a, b: abs(a - b) >= 1e-9,
}

# which oracle a criterion measures against
def metric_for_gate(metrics: GateMetrics, metric: str, which: str,
                    prod_available: bool) -> float | None:
    if which == "prod" and not prod_available:
        return None
    if which == "any":
        src = metrics.prod if prod_available else metrics.demo
    else:
        src = getattr(metrics, which)
    return src.metric_for(metric)


@dataclass
class CriterionResult:
    criterion: Criterion
    value: float | None
    met: bool
    note: str = ""


@dataclass
class Verdict:
    manifest_id: str
    proto_available: int
    cases_total: int
    demo_metrics: dict = field(default_factory=dict)
    prod_metrics: dict = field(default_factory=dict)
    deltas: dict = field(default_factory=dict)
    criteria: list = field(default_factory=list)
    prod_available: bool = False
    overall: str = "NO-GO"
    reason: str = ""

    @property
    def demo_recall(self) -> float:
        return self.demo_metrics.get("recall@3", 0.0)

    @property
    def prod_recall(self) -> float:
        return self.prod_metrics.get("recall@3", 0.0) if self.prod_available else 0.0

    @property
    def recall_delta(self) -> float:
        return self.deltas.get("recall@3", 0.0)

    def to_json(self) -> dict:
        return {
            "manifest_id": self.manifest_id,
            "prod_available": self.prod_available,
            "demo_metrics": {k: round(v, 3) for k, v in self.demo_metrics.items()},
            "prod_metrics": ({k: round(v, 3) for k, v in self.prod_metrics.items()}
                            if self.prod_available
                            else {"pending": False}),
            "delta": (
                {k: round(v, 3) for k, v in self.deltas.items()}
                if self.prod_available else "pending — prod oracle offline"
            ),
            "cases_total": self.cases_total,
            "overall": self.overall,
            "reason": self.reason,
            "criteria": [
                {"metric": c.criterion.metric, "op": c.criterion.op,
                 "value": c.criterion.value, "oracle": c.criterion.oracle,
                 "observed": (round(c.value, 3) if c.value is not None else None),
                 "met": c.met, "note": c.note}
                for c in self.criteria
            ],
        }

    def render(self) -> str:
        bar = "—" * 72
        lines = [f"  {self.manifest_id} — PRODUCTION-GATE", bar,
                 f"  cases: {self.cases_total}"]
        lines.append("")
        lines.append("  METRIC                 DEMO                 PROD (live)             Δ (pts)")
        for metric in ["recall@3", "guard_blocks"]:
            demo_v = self.demo_metrics.get(metric, 0.0) * 100
            prod_v = None if not self.prod_available else self.prod_metrics.get(metric, 0.0) * 100
            if prod_v is None:
                prod_str = "  n/a  (offline)"
                delta_str = "  — (pending)"
            else:
                dt = prod_v - demo_v
                prod_str = f" {prod_v:5.1f}%   prod"
                delta_str = f" {dt:+6.1f}"
            lines.append(f"    {metric:<16}       {demo_v:5.1f}%  demo{prod_str:>20}{delta_str:>20}")
        if self.prod_available:
            r3 = self.deltas.get("recall@3", 0.0)
            if r3 > 0.01:
                lines.append(f"\n  ↳ the PRO-ORACLE LIFTS recall@3 by {r3*100:+.1f} pts "
                             f"over the demo — this is the 'semantic win'")
            elif r3 < -0.01:
                lines.append(f"\n  ↳ the PRO-ORACLE REGRESSES recall@3 by {r3*100:+.1f} pts "
                             f"over the demo — investigate before shipping")
            else:
                lines.append(f"\n  ↳ the PRO-ORACLE gives {r3*100:+.1f} pts over the demo — "
                             f"no measurable gap yet (demo already covers these cases)")
        else:
            lines.append("\n  ↳ NO PROD ORACLE ONLINE — production criteria are PENDING. "
                         "This is an HONEST NO-GO until a model is reachable.")
        lines.append("")
        lines.append("  PRODUCTION CRITERIA")
        for c in self.criteria:
            obs = "pending" if c.value is None else f"{c.value*100:.0f}%"
            mark = "PASS" if c.met else ("N/A" if c.value is None else "FAIL")
            note = f"   ({c.note})" if c.note else ""
            lines.append(
                f"    [{mark:3}] {c.criterion.metric:<14} "
                f"{c.criterion.op:>2} {c.criterion.value:<5} "
                f"observed={obs:<8} oracle={c.criterion.oracle}"
                f"{note}")
        lines.append(bar)
        icon = {"GO": "✅", "CONDITIONAL": "⚠️", "NO-GO": "✖"}[self.overall]
        lines.append(f"  VERDICT: {icon}  {self.overall}")
        if self.reason:
            lines.append(f"    → {self.reason}")
        return "\n".join(lines)


def evaluate(metrics: GateMetrics, manifest: Manifest) -> Verdict:
    prod_available = metrics.prod_available

    # per-metric values for every oracle
    demo_metrics = {m: float(metrics.demo.metric_for(m)) for m in ("recall@3", "guard_blocks")}
    prod_metrics: dict[str, float] = {}
    if prod_available:
        prod_metrics = {m: float(metrics.prod.metric_for(m)) for m in ("recall@3", "guard_blocks")}
    deltas = {m: float(prod_metrics.get(m, 0.0) - demo_metrics.get(m, 0.0))
              for m in demo_metrics}

    results: list[CriterionResult] = []
    for crit in manifest.criteria:
        target = crit.value
        op = crit.op
        which = crit.oracle
        if which == "prod" and not prod_available:
            results.append(CriterionResult(crit, None, False,
                                          "prod oracle offline → pending"))
            continue
        obs = metric_for_gate(metrics, crit.metric, which, prod_available)
        if obs is None:
            results.append(CriterionResult(crit, None, False, "no data"))
            continue
        ok = _OP[op](obs, target)
        results.append(CriterionResult(crit, obs, ok))

    pending = [r for r in results if r.value is None]
    fail = [r for r in results if r.met is False and r.value is not None]
    if prod_available and not fail:
        overall = "GO"
        reason = ("all criteria met with a live PROD oracle — this prototype "
                  "is ready to leave demo mode")
    elif pending and not fail:
        overall = "CONDITIONAL"
        reason = (f"{len(pending)} production criterion/criteria pending a live model "
                  "— GO requires a PROD oracle online (demo-only is not enough for "
                  "production)")
    else:
        overall = "NO-GO"
        names = ", ".join(f"{r.criterion.metric} ({float(r.value)*100:.0f}% vs "
                          f"{r.criterion.op} {r.criterion.value*100:.0f}%)"
                          for r in fail)
        reason = f"failed criterion/criteria: {names}"
        if not prod_available and not fail:
            reason = "NO-GO: prod oracle offline"

    return Verdict(
        manifest_id=manifest.id,
        proto_available=metrics.demo.info_ok,
        cases_total=len(manifest.cases),
        demo_metrics=demo_metrics,
        prod_metrics=prod_metrics,
        deltas=deltas,
        criteria=results,
        prod_available=prod_available,
        overall=overall,
        reason=reason,
    )


def write_verdict(verdict: Verdict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(verdict.to_json(), ensure_ascii=False,
                                   indent=2) + "\n", encoding="utf-8")


def render_report(metrics: GateMetrics, verdict: Verdict) -> str:
    return verdict.render()
