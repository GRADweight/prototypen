# GRADweight — prototypen

**Prototypen-Katalog (1–20): jeder Prototyp ein lauffähiges Mini-Repo
mit einem sichtbaren Produktionstest.**

Der Punkt dieses Repos ist nicht "es läuft" — es ist **"wir können
beweisen, wann ein Prototyp in die Produktion kann, und wann nicht"**
— mit einem **sichtbaren Delta** zwischen Demo und Produktiv.

## Was jetzt lauffähig ist (3 Prototypen, 1 Gate)

Alle drei laufen auf demselben `gw_proto`-Production-Gate (dual-oracle,
DEMO vs. PROD):

| # | Prototyp | Domäne | DEMO | PROD | Δ | Verdict |
|---|---|---|---|---|---|---|
| 01 | RAG-Chatbot | semantisch | 50% | 100% (live) | **+50 pts** | ✅ GO* |
| 02 | Rechnungs-Extraktion | deterministisch | 75% | 75% | +0 | ✅ GO |
| 03 | E-Mail-Triage | deterministisch | 100% | 100% | +0 | ✅ GO |

\* `01` ist GO **nur wenn `nomic-embed-text` online ist**
(Ollama `localhost:11434`). In CI (kein Modell) gibt er ehrlich
`CONDITIONAL` — kein vorgetäuschter Erfolg.

## Das Geniale: der Delta ist das Produkt

Der semantische Fall in `01` ("Wenn ich krank bin, ab wievielter
Arbeitstag brauche ich ein ärztliches Attest?" —
englisch zum deutschen Corpus):

```
DEMO (bag-of-words)   50%   ← findet den Fall nicht (Wort-Überlapp)
PROD (nomic-embed)   100%   ← findet den Fall per Bedeutung
Δ  =  +50 Punkte
```

Das ist *nicht simuliert*: der StubClient versagt, das echte
Embedding-Modell gewinnt. Der Delta von +50 ist der Moment, wo wir
in Produktion gehen.

## DRY-Proof: 3 Domänen, 1 Gate

Jeder Prototyp kostet **`manifest.json` + ~40 Zeilen `pipeline.py`** —
nie einen zweiten Gate-Runner:

```
prototypes/01-rag-chatbot/            → manifest.json + code/main.py (RAG-Pfad)
prototypes/02-rechnungs-extraktion/   → manifest.json + pipeline.py (Extraktion)
prototypes/03-email-triage/           → manifest.json + pipeline.py (Klassifikation)
```

Drei völlig verschiedene Domänen (RAG / Extraktion / Triage) laufen
auf **einem** Runner. Der nächste Prototyp kostet ~15 Minuten.

## Schnellstart

```bash
# 1. gw_proto ist in vendor/ (stdlib-Only, kein pip)
# 2. Offline-Gate (CI-Äquivalent — ehrlich, kein Modell):
python -m gw_proto prototypes/01-rag-chatbot/manifest.json --no-prod

# 3. Live-Gate (mit Ollama + echtem Embedding):
docker run -p 11434:11434 ollama/ollama
ollama pull nomic-embed-text
python -m gw_proto prototypes/01-rag-chatbot/manifest.json

# 4. Alter Smoke-Test (kompatibel, offline):
python3 prototypes/01-rag-chatbot/code/main.py "Wie viele Ferientage habe ich im ersten Dienstjahr?"
```

## Verdict-Klassik

| Verdict | Bedeutung | CI-Exit |
|---|---|---|
| ✅ GO | Alle Kriterien erfüllt, PROD online | 0 |
| ⚠️ CONDITIONAL | Reif, aber PROD-Modell offline | 0 (ehrlich) |
| ✖ NO-GO | Kriterien verfehlt | 1 |

**CONDITIONAL ist der ehrliche Zustand** — wir könnten morgen in
Produktion, es bräuchte ein Modell. Nicht ein vorgetäuschtes
"OK, alles grün".

## Ehrliche Grenzen

- **3 von 20 Prototypen** haben jetzt Code + Gate (Roadmap:
  `~/.hermes/plans/2026-10-22_prototypen-m2-umruebung.md`).
- In CI (GitHub-Actions, kein Ollama) geben RAG-Prototypen
  `CONDITIONAL`, nicht `GO` — das ist **beabsichtigt** und zeigt,
  dass unser Gate **keinen** vorgetäuschten Erfolg liefern kann.
- `nomic-embed-text` ist ein 137M-Modell für die Demo; für Produktion
  sollte ein feingranuliertes Embedding oder ein Domain-Embedding
  genommen werden.
- `gw_shared_lib/vendor/` ist ein Snapshot v0.1.0 (mit Drift-Guard:
  16 Injection-Signaturen — Abweichung bricht den CI).

## Kontakt

**edin@gradweight.ch** · [gradweight.ch](https://gradweight.ch)
