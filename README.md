# GRADweight — prototypen

**Prototypen-Katalog (1–20): jeder Prototyp ein lauffähiges Mini-Repo.**

Zwei Prototypen sind jetzt lauffähig über `gw-shared-lib`:

| # | Prototyp | Status | Code |
|---|---|---|---|
| 1 | RAG-Chatbot für interne Dokumente | ✅ smoke-lauffähig (über shared-lib) | `prototypes/01-rag-chatbot/code/` |
| 2 | Rechnungs-Extraktion | ✅ smoke-lauffähig (über shared-lib) | `prototypes/02-rechnungs-extraktion/code/` |
| 3 | E-Mail-Triage | 📋 geplant (über shared-lib guard) | — |
| 7 | Meeting-Assistent | 📋 geplant (über shared-lib audit) | — |

## Schnellstart (1–2)

```bash
# 1. shared-lib einbinden (kein pip nötig — relativ-Pfad)
# 2. RAG-Chatbot (offline, ohne Netz)
cd prototypes/01-rag-chatbot
python3 code/main.py "Wie viele Ferientage habe ich im ersten Dienstjahr?"

# 3. Rechnungs-Extraktion (Demo mit Fake-Rechnung)
cd prototypes/02-rechnungs-extraktion
python3 code/main.py
```

## Ehrliche Grenzen

Beide Prototypen nutzen `gw-shared-lib` (6 Bausteine, stdlib-only).
Die `StubClient` (bag-of-words) reicht für **Retrieval-Logik**, aber
nicht für semantische Ähnlichkeit. Für Produktion: `GW_INFER_URL` +
ein echtes Embedding-Modell (nomic-embed-text via Ollama).

Weitere 18 Prototypen (Nr. 3–20) sind für spätere Iterationen geplant.
Jeder Prototyp baut auf den **gleichen** 6 Bausteinen — kein
Big-Ball-of-Mud.

**Kontakt:** edin@gradweight.ch · gradweight.ch
