"""pipeline.py — Offerten-/Angebotsgenerator (Katalog-Nr. 5).

Der DRY-Proof #2: ein komplett neuer Domäne (kein RAG, kein LLM), die
trotzdem exakt dieselbe gw_proto-Signatur nutzt —
`run(case, oracle_spec, *, use_stub=False, manifest=None) -> dict` —
und damit denselben Gate, dieselben Δ-Reports, dasselbe JSON-Verdict.

Katalog-Prinzip Nr. 5: Preislogik ist REGULBAISIERT, nie dem LLM
ueberlassen. Demnach ist der Generator deterministisch und
DEMO == PROD == regelbasierter Generator. Δ = 0 ist kein Mangel,
sondern das Merkmal (reproduzierbare Offerten, kein LLM-Zufall).

Der Fail-loud ist o-missing: fehlt eine Mengenangabe, wird KEIN
Total erfinden (no false cite) — sondern 'error:missing' als
top_source. Das ist das Verkaufsargument 'wir halluzinieren keine
Preise' (DSG-konform, keine Halluzination).

Ein PROD-Upgrade (LLM fuer den Offerten-Text, Live-Preislisten-Sync)
laeuft auf derselben run()-Signatur — nur der Text-Generator wechselt,
kein zweiter Gate-Runner.
"""
from __future__ import annotations

import json
import re

from gw_shared_lib import analyse, GuardPipeline  # noqa: F401

# --- 1. Guard: ist die Anfrage eine Prompt-Injection? (fail-closed) ---
def _is_injection(text: str):
    return GuardPipeline().run(text)


# --- 2. Preisliste (KATALOG: regelbasiert, nie dem LLM ueberlassen!) ---
# In einer Realfirma: aus einer Excel/CSV-Preisliste geladen.
PRICE_LIST = {
    "beratungstag": 750.0,
    "kartons": 8.0,
    "transport": 450.0,
    "projekttag": 1200.0,
    "workshop": 900.0,
    "halbtagesberatung": 400.0,
}


def _build_offerte(payload: dict) -> dict:
    """Gibt eine strukturierte Offerte zurueck, ODER (bei fehlenden Inputs)
    `error:missing` — kein halluziniertes Total.

    Returns: {ok, total, positions, error, cite_source, cite_field, note}
    """
    service = (payload.get("service") or "").strip()
    positions_in = payload.get("positions") or []
    out = {"ok": False, "total": 0.0, "positions": [], "error": "",
           "cite_source": "", "cite_field": "", "note": ""}
    if not service:
        out["error"] = "missing-service"
        out["cite_source"] = "error:missing"
        out["note"] = "kein service — kein Offerten-Text, kein Total (fail-loud)"
        return out
    total = 0.0
    for pos in positions_in:
        name = (pos.get("name") or "").strip()
        qty = pos.get("qty")
        unit = pos.get("unit") or "Stueck"
        key = name.lower()
        if key not in PRICE_LIST:
            out["error"] = f"unbekannter position: {name!r}"
            out["cite_source"] = "error:unknown-position"
            out["note"] = f"Position {name!r} nicht in Preisliste"
            out["ok"] = False
            return out
        if qty in (None, 0, "") or not isinstance(qty, (int, float)):
            out["error"] = "missing-quantity"
            out["cite_source"] = "error:missing"
            out["note"] = f"Position {name!r} ohne Menge — kein Total (fail-loud)"
            out["ok"] = False
            return out
        price = PRICE_LIST[key]
        line_total = price * float(qty)
        total += line_total
        # cite per Position (deterministisch, regelbasiert)
        out["positions"].append({
            "name": name, "unit": unit, "qty": int(qty) if float(qty).is_integer() else qty,
            "unit_price": price, "line_total": round(line_total, 2),
        })
    if out["positions"]:
        out["ok"] = True
        out["total"] = round(total, 2)
        out["cite_source"] = "offer/total"
        out["cite_field"] = "total"
        out["note"] = f"offerte fuer {service}: {len(out['positions'])} Position(en), " \
                      f"Total CHF {out['total']:.2f} (regelbasiert, kein LLM)"
    else:
        out["error"] = "no-positions"
        out["cite_source"] = "error:missing"
        out["note"] = "keine Positionen — kein Total (fail-loud)"
    return out


def run(case, oracle_spec, *, client=None, use_stub=False, manifest=None) -> dict:
    """Ein Offerten-Fall durch Guard + regelbasierten Generator.

    Manifest-Case-Shape:
      case.question = JSON-String {"service":..., "positions":[{name,unit,qty}]}
                      (oder im Injection-Fall: plain Text/JSON — der Guard
                       blockiert den Rest)
      case.golden   = erwartete Source-Präfix (z.B. "total" / "error:missing")
      case.expect   = info | guard_block
    """
    raw = case.question or ""
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        # kein valide JSON — der Guard muss zuerst pruefen
        gr = _is_injection(raw)
        findings = analyse(raw)
        if gr.blocked:
            return {
                "case_expect": case.expect,
                "blocked": 1, "blocked_reason": gr.reason or "",
                "hit": case.expect == "guard_block",
                "cites": [], "top_source": "", "top_score": 0.0,
                "note": f"guard blocked: {findings.primary_category}",
            }
        return {
            "case_expect": case.expect, "blocked": 0,
            "blocked_reason": "", "hit": False,
            "cites": [], "top_source": "", "top_score": 0.0,
            "note": "question ist kein valide JSON"
        }

    text = json.dumps(payload, ensure_ascii=False)

    # 1. Guard zuerst — eine Injection wird nie gebaut/versandt.
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

    # 2. Regelbasierter (deterministischer) Offerten-Generator.
    off = _build_offerte(payload)

    # 3. Cites-Shape (RAG-format, damit der Gate den Δ richtig rechnet):
    cites = []
    if off["ok"]:
        for p in off["positions"]:
            cites.append({
                "source": f"offer/position:{p['name'].lower()}",
                "confidence": 1.0,
                "text": f"{p['name']} x{p['qty']} = CHF {p['line_total']:.2f}",
            })
    elif off["error"]:
        cites.append({
            "source": off["cite_source"],
            "confidence": 1.0 if off["error"].startswith("missing") else 0.0,
            "text": off["error"],
        })

    out = {
        "case_expect": case.expect,
        "blocked": 0, "blocked_reason": "",
        "cites": cites,
        "top_source": off["cite_source"],
        "top_score": (1.0 if off["ok"] or off["error"].startswith("missing") else 0.0),
        "note": off["note"],
    }
    # info-Fall: hit nur wenn golden (= "total") im top_source vorkommt
    # ODER wenn golden = "error:missing" vorkommt.
    if case.expect == "info" and case.golden:
        out["hit"] = bool(case.golden in off["cite_source"])
    elif case.expect == "guard_block":
        out["hit"] = False
    elif case.expect == "no_answer":
        out["hit"] = False
    return out
