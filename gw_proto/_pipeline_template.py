"""pipeline.py — ein neuer Prototyp, ganz ohne neuen Gate-Runner.

Nicht-RAG-Fälle (E-Mail-Triage, Rechnung, Offerte) bringen hier nur das
eine Modul mit. Der Runner erkennt `pipeline.py` automatisch, ruft
`run()` auf mit demselben Result-Format wie RAG, und der
Production-Gate / DELTA-Report / das JSON-Verdict kommen aus gw_proto.

Das ist der DRY-Proof: E-Mail-Triage ist ein völlig neuer Prototyp,
aber es kostet eine Manifest + diese ~40 Zeilen, nie einen zweiten
Gate-Runner.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

from gw_shared_lib import analyse, Chunk, GuardPipeline, audit_action  # noqa: F401

# ---------------------------------------------------------------------------
# E-Mail-Triage (Nr. 3, Katalog). Offline-lauffähig, ohne Modell.
#
# Logik:
#   1. Guard: ist der Body ein Prompt-Injection?  (Guard-Pipeline fail-closed)
#   2. Klassifikation: regex-Heuristik auf subject/body — offline,
#      deterministisch, kein Modell nötig (kein ML-Hallazination).
#   3. Antwortentwurf: aus der Kategorie (kein LLM-Text, nur Vorlage),
#      kein auto-Versand — ein Mensch darf freigeben.
#
# In der Produktion (PROD-Orakel) läuft dieselbe Signatur mit einem
# echten LLM-Judge (nomic-embed-text / ein kleines Chat-Modell) statt
# dem stub — der Code-Pfad ist derselbe, nur das Modell wechselt.
# ---------------------------------------------------------------------------

_KLASS = [
    ("dringlich", re.compile(r"(?:dringlich|urgent|sofort|notfall|überfällig|"
                              r"überfäll|fällig|vertrag|kündigung)", re.I)),
    ("normal", re.compile(r".")),   # der Fallback
]


def _classify(subject: str, body: str) -> tuple[str, float, str]:
    s = (subject or "") + " " + (body or "")
    for name, rx in _KLASS:
        if rx.search(s):
            conf = 0.9 if name == "dringlich" else 0.7
            action = ("Entwurf für 24h-Schluss" if name == "dringlich"
                      else "Entwurf, Mensch prüft")
            return name, conf, action
    return "spam", 0.6, "Spam — löschen"


def run(case, oracle_spec, *, client=None, use_stub=False, manifest=None) -> dict:
    """Ein E-Mail-Triage-Fall.

    Manifest-Shape für diese Cases:
      case.question   = ein JSON-String: {"subject":..., "body":...}
      case.golden     = die erwartete Kategorie ("dringlich"/"normal"/"spam")
    """
    import json
    raw = case.question
    try:
        email = json.loads(raw)
    except Exception:
        return {
            "case_expect": case.expect,
            "blocked": 0, "blocked_reason": "parse-error",
            "hit": False, "cites": [], "top_source": "",
            "top_score": 0.0, "note": "question is not JSON",
        }

    subject = email.get("subject", "")
    body = email.get("body", "")

    # 1. Guard (fail-closed): Prompt-Injection?
    findings = analyse(subject + " " + body)
    gr = GuardPipeline().run(subject + " " + body)
    if gr.blocked:
        return {
            "case_expect": case.expect,
            "blocked": 1, "blocked_reason": gr.reason,
            "hit": case.expect == "guard_block",
            "cites": [], "top_source": "", "top_score": 0.0,
            "note": findings.primary_category,
        }

    # 2. Klassifikation (offline deterministisch)
    klass, conf, action = _classify(subject, body)
    # 3. Response-Vorlage
    out = {
        "case_expect": case.expect,
        "blocked": 0, "blocked_reason": "",
        "cites": [{"source": "triage/regex", "confidence": conf}],
        "top_source": klass, "top_score": conf,
        "note": f"classified as {klass}, action={action}",
    }
    if case.expect == "info":
        out["hit"] = (klass == case.golden)
    elif case.expect == "guard_block":
        out["hit"] = False
    elif case.expect == "no_answer":
        out["hit"] = False
    return out
