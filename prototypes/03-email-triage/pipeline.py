"""pipeline.py — E-Mail-Triage (Katalog-Nr. 3).

Der DRY-Proof: ein völlig neuer Domäne (kein RAG), die trotzdem exakt
dieselben gw_proto-Primitive nutzt — Guard fail-closed, klassifizierende
Heuristik, ein Result-Dict im RAG-Format. Der Gate-Runner erkennt dieses
Modul automatisch; Gate, Δ-Report und JSON-Verdict kommen aus gw_proto.

Ein neuer Prototyp kostet also nur:
  - eine manifest.json   (cases + production_criteria)
  - diesen ~40-Zeilen pipeline.py
Nie einen zweiten Gate-Runner.
"""
from __future__ import annotations
import json
import re

from gw_shared_lib import analyse, GuardPipeline  # noqa: F401

# --- 1. Guard: ist der Body ein Prompt-Injection? (fail-closed) ---
def _is_injection(text: str):
    return GuardPipeline().run(text)

# --- 2. Klassifikation: deterministische Heuristik, kein Modell ---
_KLASS = [
    ("dringlich", re.compile(
        r"(?:dringlich|urgent|sofort|notfall|überfällig|überfäll|fristig|"
        r"kündigung|vertrag endet|bitte bis|klären|dringlich)", re.I)),
]

def _classify(subject: str, body: str) -> tuple[str, float, str]:
    s = f"{subject} {body}".lower()
    for name, rx in _KLASS:
        if rx.search(s):
            return name, 0.9, "Entwurf für 24-Stunden-Schluss"
    return "normal", 0.7, "Standardentwurf, Mensch prüft"


def run(case, oracle_spec, *, client=None, use_stub=False, manifest=None) -> dict:
    """Ein E-Mail-Triage-Fall durch Guard + Heuristik.

    Manifest-Case-Shape:
      case.question = JSON-String {"subject":..., "body":...}
      case.golden   = erwartete Kategorie ("dringlich" | "normal")
      case.expect   = info | guard_block
    """
    try:
        email = json.loads(case.question)
    except Exception:
        return {"case_expect": case.expect, "blocked": 0, "blocked_reason": "parse-error",
                "hit": False, "cites": [], "top_source": "", "top_score": 0.0,
                "note": "question is not JSON"}

    subject = email.get("subject", "")
    body = email.get("body", "")
    text = f"{subject} {body}"

    # 1. Guard zuerst — eine Injection wird nie klassifiziert.
    gr = _is_injection(text)
    findings = analyse(text)
    if gr.blocked:
        return {
            "case_expect": case.expect,
            "blocked": 1, "blocked_reason": gr.reason or "",
            "hit": case.expect == "guard_block",
            "cites": [], "top_source": "", "top_score": 0.0,
            "note": f"guard blocked: {findings.primary_category}",
        }

    # 2. Klassifikation (offline, deterministisch — kein ML-Halluzination).
    klass, conf, action = _classify(subject, body)
    out = {
        "case_expect": case.expect,
        "blocked": 0, "blocked_reason": "",
        "cites": [{"source": "triage/regex", "confidence": conf, "text": subject[:60]}],
        "top_source": klass, "top_score": conf,
        "note": f"classified as {klass} → {action}",
    }
    if case.expect == "info":
        out["hit"] = (klass == (case.golden or klass))
    elif case.expect == "guard_block":
        out["hit"] = False
    elif case.expect == "no_answer":
        out["hit"] = False
    return out
