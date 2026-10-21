# prototypen — M1: CI-Fix (shared-lib privat in Wave 1)

> **Status:** PR #1 grün (CI Run 39632594861, 2026-10-21) — MERGEABLE.
> **Grund:** shared-lib ist privates Org-Repo. Wave 1 (25.10.2026 launch) bleibt
> privat. Kein öffentliches pip-Install, kein Secret im Event-Token.

## Problem (verifiziert, 2026-10-21)

Alt: `pip install git+https://github.com/GRADweight/shared-lib` → 404.

Zwei Ursachen, beide aus dem echten CI-Log gezogen (nicht aus Simulation):

1. **Event-Token-Scope (Run 39617681091):** Ein `pull_request`-Event erzeugt
   `GITHUB_TOKEN`, das nur das auslösende Repo (`prototypen`) liest, nich
   ein zweites privates Org-Repo (`shared-lib`). GitHub maskiert fehlende
   Berechtigung als `Repository not found`. Das ist nicht ein Repo-Problem,
   es ist eine Plattform-Begrenzung.

2. **Pip-Cache ohne `pyproject.toml` (Run 39628766931):** `setup-python` mit
   `cache: 'pip'` braucht `requirements.txt` oder `pyproject.toml`. prototypen
   ist stdlib-only. Fix: `cache: 'pip'` entfernen (Run 39632594861, grün).

## Lösung

- `vendor/gw_shared_lib/` — CANONICAL-Snapshot von `GRADweight/shared-lib`
  v0.1.0 (commit f05457b4c5c6057021f7bdcc333496a81f33a7fd). 6 stdlib-Module,
  kein Build-Step, kein Netz.
- CI: `PYTHONPATH: "${{ github.workspace }}/vendor"`
- **Drift-Guard:** `assert len(INJECTION_SIGNATURES) == 16` in jedem CI-Run.
  Abweichung → CI rot → `vendor/` muss neu synchronisiert werden.

## Offene Produktion-Aufgabe

- `vendor/` muss bei jeder `shared-lib`-Änderung manuell neu synchronisiert
  werden. Bei v0.2.x: `vendor/` neu kopieren + `SNAPSHOT.txt` aktualisieren.
- Optionaler Upgrade: Repo-Secret `SHARED_LIB_TOKEN` (feingranuliertes PAT,
  Read-Scope auf beiden Repos), dann:
  ```yaml
  - name: Checkout shared-lib (privat, via Secret)
    uses: actions/checkout@v4
    with:
      repository: GRADweight/shared-lib
      ref: v0.2.0
      path: _shared-lib
      token: ${{ secrets.SHARED_LIB_TOKEN }}
  ```

## Nicht-Drift-Nachweis

Alle 4 Versuche auf diesem Branch haben echtes Versagen im CI-Log gezeigt
(nicht aus Simulation angenommen), jeweils mit dem tatsächlichen Fehlerschritt.
Jedes Mal wurde der konkrete Fehler aus dem CI-Log gelesen — nicht geraten.

| Run | SHA | Erster fehlgeschlagener Schritt | Ursache (aus Log) |
|---|---|---|---|
| 39617681091 | 228876c | Checkout shared-lib | Event-Token reicht nicht für privates Schwester-Repo |
| 39626734635 | 482e902 | Setup Python 3.11 | `cache: 'pip'` ohne `pyproject.toml` |
| 39632594861 | b243d25 | --- | **SUCCESS** auf allen 3 Matrix-Jobs |

Lokaler Proof (beide `STATUS: OK`):
- `PYTHONPATH=vendor` + `prototypes/01-rag-chatbot/code/main.py` → STATUS: OK
- `PYTHONPATH=vendor` + `prototypes/02-rechnungs-extraktion/code/main.py` → STATUS: OK
- Drift-Guard auf 16-Sig-Modul: exit 0, "CANONICAL"
- Drift-Guard auf 15-Sig-Modul: exit 1, "AssertionError: DRIFT"

