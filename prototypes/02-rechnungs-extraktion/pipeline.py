"""pipeline.py — Rechnungs-Extraktion (Katalog-Nr. 2).

Der dritte Beweis von DRY: ein drittes Domäne, die dieselben
gw_proto-Primitive nutzt. Die Extraktion ist deterministisch (Regex),
daher ist Delta = 0 zwischen DEMO und PROD — *das ist das Merkmal*:
deterministisch = reproduzierbar = kein LLM-Zufall. Für einen
Vision-LLM-Upgrade (PROD) läuft dieselbe Signatur mit einem LLM-Judge.

Manifest-Case-Shape für Extraktion:
  case.question  = JSON-String: {"invoice": "...text..."}
  case.golden    = erwartetes Feld-Name ("date" | "supplier" | "total" | "vat")
  case.expect    = "info"  => Feld muss gefunden sein
"""
from __future__ import annotations
import json
import re


_KLEIN = {
    "date": re.compile(r"Rechnung vom (\d{2}\.\d{2}\.\d{4})"),
    "invoice_nr": re.compile(r"(?:Nr\.|Nummer\s*:)\s*(\d+)"),
    "supplier": re.compile(r"Lieferant:\s*(.*?)(?:\n|,|$)", re.I),
    "total": re.compile(r"Endsumme:\s*(CHF\s*[\d.,]+)", re.I),
    "vat": re.compile(r"MwSt:\s*(CHF\s*[\d.,]+)", re.I),
}


def _extract(text: str, field: str):
    rx = _KLEIN.get(field)
    if not rx:
        return None
    m = rx.search(text)
    return m.group(1).strip() if m else None


def run(case, oracle_spec, *, use_stub=False, manifest=None) -> dict:
    try:
        payload = json.loads(case.question)
        invoice = payload.get("invoice", "")
    except Exception:
        return {"case_expect": case.expect, "blocked": 0, "blocked_reason": "parse-error",
                "hit": False, "cites": [], "top_source": "", "top_score": 0.0,
                "note": "question is not JSON"}

    golden = (case.golden or "date").strip().lower()
    val = _extract(invoice, golden)
    out = {
        "case_expect": case.expect,
        "blocked": 0, "blocked_reason": "",
        "cites": ([{"source": f"field:{golden}", "text": val}] if val else []),
        "top_source": golden, "top_score": 1.0 if val else 0.0,
        "note": f"extracted {golden} -> {val!r}",
    }
    if case.expect == "info":
        out["hit"] = bool(val)
    return out
