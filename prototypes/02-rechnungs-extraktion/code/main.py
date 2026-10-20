"""Rechnungs-Extraktion — smoke-demo über gw-shared-lib (offline).

Nutzt gw-shared-lib für den Audit-Trail. Für die Extraktion selbst:
einfacher Regex-Parser (deterministisch, kein ML). Für echte
Extraktion: ein Vision-LLM (Claude/GPT-4o) oder ein
`pdfplumber`-Pass mit Strukturerhalt.

Die Demo zeigt:
  - Eingangsdatei: Fake-Rechnung (kein echte Daten, kein Kundendaten)
  - Extraktion: Datum, Nr, Lieferant, Endsumme, MwSt
  - Audit: gw-shared-lib audit.AuditLog
"""
from __future__ import annotations
import sys
import pathlib
import re

# CANONICAL gw-shared-lib: in CI via pip, lokal via Sibling `../shared-lib`
try:
    from gw_shared_lib import audit
except ImportError:
    sys.path.insert(
        0,
        str(pathlib.Path(__file__).resolve().parents[4] / "shared-lib"),
    )
    from gw_shared_lib import audit

# Fake-Rechnung (demo, kein Kundendaten)
FAKE_INVOICE = (
    "Rechnung vom 15.03.2026, Nr. 2026-0421\n"
    "Lieferant: Muster AG, 4051 Basel\n"
    "Position 1: 2 Stück, Preis CHF 45.00, MwSt 8%\n"
    "Position 2: 1 Stück, Preis CHF 120.00, MwSt 8%\n"
    "Total: CHF 165.00, MwSt: CHF 13.20, Endsumme: CHF 178.20\n"
)


def parse_simple(text: str) -> dict:
    """Ein einfacher Regex-Parser (deterministisch).

    Für Produktion: strukturierte Extraktion via Vision-LLM oder
    `pdfplumber` mit Field-Mapping. Hier: Regex für die Demo.
    """
    r: dict = {}
    m = re.search(r"Rechnung vom (\d{2}\.\d{2}\.\d{4})", text)
    if m:
        r["date"] = m.group(1)
    m = re.search(r"(Nr\.\s*\d+)", text)
    if m:
        r["invoice_nr"] = m.group(1)
    m = re.search(r"Lieferant: (.*?)(?:\n|,)", text)
    if m:
        r["supplier"] = m.group(1).strip()
    m = re.search(r"Endsumme: (CHF [\d.,]+)", text)
    if m:
        r["total"] = m.group(1)
    m = re.search(r"MwSt: (CHF [\d.,]+)", text)
    if m:
        r["vat"] = m.group(1)
    return r


def main() -> int:
    r = parse_simple(FAKE_INVOICE)

    print("Rechnungs-Extraktion (demo)")
    for k in ("date", "invoice_nr", "supplier", "total", "vat"):
        if k in r:
            print("  %-8s %s" % (k + ":", r[k]))

    if r.get("invoice_nr"):
        a = audit.AuditLog("./.audit/demo.jsonl")
        audit.audit_action(
            a, "rechnung_parsed",
            actor="demo",
            input="invoice.txt",
            output=r,
            invoice_nr=r.get("invoice_nr", ""),
            total=r.get("total", ""),
            supplier=r.get("supplier", ""),
        )
        print("  [AUDIT] 1 Eintrag geschrieben (gw-shared-lib audit)")

    ok = all(k in r for k in ("date", "supplier", "total"))
    print("\nSTATUS: " + ("OK" if ok else "TEILGEFUNDEN"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
