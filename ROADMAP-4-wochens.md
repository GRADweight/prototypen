# ROADMAP — 4 Wochen / 15 Prototypen (Katalog-Nr. 7-20)

**Kontext:** Am 2026-10-22 stehen 6 von 20 Prototypen in `prototypes/`
mit einem lauffähigen, ehrlichen Production-Gate (6/6 gate-läufe, 3
GO + 3 CONDITIONAL live, alle mit sichtbarem Δ und
fail-closed Guards). Die nächsten 14 Prototypen (Nr. 7-20) folgen
dem selben Muster — `manifest.json` + (optional) `pipeline.py` —
jeder ~15-30 Minuten (nur bei ML-schweren Fällen länger).

---

## Woche 1 — 2026-10-23 bis 2026-10-27: 5 Prototypen (Nr. 7, 8, 9, 10, 11)

Brot-und-Butter-Ende + Anfang Governance-Einstieg.

| Nr. | Prototyp | Schwierigkeit | Typ | Aufwand |
|-----|----------|:---:|---|:---:|
| 7 | Meeting-Assistent (Transkript + Aufgaben) | 3 | RAG + Extraktion | 45 Min |
| 8 | Vertragsanalyse & Klausel-Check | 6 | RAG + Guard + Taxonomie | 60 Min |
| 9 | Mehrsprachen-Übersetzung DE/FR/IT | 4 | Translation-Wrapper | 45 Min |
| 10 | Marketing-Content (Brand Voice) | 3 | RAG-Wrapper | 30 Min |
| 11 | CV-Screening-Assistent | 5 | Extraktion + Guard + Bias | 75 Min |

**Fokuswoche:** RAG-Wrapper + Extraktion + ein Bias-Blocker
(Nr. 11). 3 neue pipeline.py, 2 reine RAG-Wrapper.

**Akzeptanz:**
- 10 Prototypen (Nr. 1-11) im `prototypes/` Verzeichnis mit
  lauffähigem Manifest.
- Alle 10 haben mindestens 1 `guard_block`-Case.
- CI.yml läuft grün (oder: offline CONDITIONAL, live GO — je
  nach Orakel-Verfügbarkeit).
- 5 Prototypen mit einem sichtbaren semantic-Delta (engl./
  lexikal-verschobene Fragen).

---

## Woche 2 — 2026-10-28 bis 2026-11-03: 4 Prototypen (Nr. 12, 13, 14, 15)

Schwierigere Stufe: Vision (12, 17), ML-Klassik (14), Audio (15).

| Nr. | Prototyp | Schwierigkeit | Typ | Aufwand |
|-----|----------|:---:|---|:---:|
| 12 | OCR Formulare & Handschrift | 5 | Vision-LLM-Wrapper | 60 Min |
| 13 | Compliance-Dokumenten-Check | 5 | RAG + Guard + Taxonomie | 60 Min |
| 14 | Verkaufs-/Bedarfsprognose | 7 | Zeitreihen-ML (Prophet) | 90 Min |
| 15 | Telefon-/Voicebot | 7 | ASR + TTS + LLM | 90 Min |

**Fokuswoche:** 15 braucht ein ASR (Whisper) + ein TTS + ein
Chatter — das ist der komplexeste Prototyp im Katalog.
14 braucht ein echtes ML-Modell (Prophet, statsmodels) —
nichts mit RAG. Die anderen 2 bleiben im RAG-Wrapper-Bereich.

**Akzeptanz:**
- 15 Prototypen (Nr. 1-15) im `prototypes/` Verzeichnis.
- 5 neue Prototypen (Nr. 11-15) mit mindestens 1 semantic-Delta
  oder 1 ML-Evaluation.
- CI.yml läuft grün.
- Nr. 12 (OCR) und Nr. 15 (Voicebot) mit echtem Modell-
  Call (nicht nur Wrapper — falls Ollama-Runner mit
  Vision/Audio-Modell aktiv ist).

---

## Woche 3 — 2026-11-04 bis 2026-11-10: 3 Prototypen (Nr. 16, 17, 18)

Schwerste Stufe: Recommendation, CV, Anomaly-ML.

| Nr. | Prototyp | Schwierigkeit | Typ | Aufwand |
|-----|----------|:---:|---|:---:|
| 16 | Produktempfehlungs-Engine | 6 | Collaborative Filtering + RAG | 75 Min |
| 17 | Visuelle Qualitätskontrolle | 8 | CV (YOLO / OpenCV / Vision-LLM) | 120 Min |
| 18 | Anomalieerkennung Buchhaltung | 7 | Anomaly-Detection (Isolation Forest) | 90 Min |

**Fokuswoche:** 3 Prototypen, alle datenabhängig und ML-lastig.
Das ist der kritische Schnitt in der Roadmap: ab hier
sind die Prototypen *nicht mehr RAG-wrappbar* — jeder
braucht ein eigenes Datenformat, ein eigenes Modell, ein
eigenes Eval-Setup. Die `pipeline.py` wird jetzt *der* Punkt,
wo der Aufwand liegt.

**Akzeptanz:**
- 18 Prototypen (Nr. 1-18) im `prototypes/` Verzeichnis.
- 3 neue Prototypen (Nr. 16-18) mit echtem ML-Eval (nicht
  nur Wrapper).
- CI.yml läuft grün (oder: ML-prototypen CONDITIONAL, weil
  kein 24/7 GPU-Runner — ehrlich).

---

## Woche 4 — 2026-11-11 bis 2026-11-17: 2 Prototypen (Nr. 19, 20)

Letzter Schnitt: Predictive Maintenance + Dev-Assistent.

| Nr. | Prototyp | Schwierigkeit | Typ | Aufwand |
|-----|----------|:---:|---|:---:|
| 19 | Predictive Maintenance | 8 | IoT-Sensorik + ML | 120 Min |
| 20 | Interner Dev-Assistent (On-Prem) | 6 | RAG + LSP + Tool-Use | 90 Min |

**Fokuswoche:** 20 ist der *Meta-Prototyp*: `gw_proto` als
ein Prototyp — `gw_proto` als `prototypes/00-gw-proto/manifest.json`
mit 12 Fällen (jeder `gw_shared_lib`-Primitive). Das ist
der DRY-Proof in Reinform: der Gate, der die anderen 19
Gate-checkt.

19 ist der schwerste Prototyp im Katalog (Schwierigkeit 8, kein
KMU ohne IoT-Sensorik + Datenwissenschaftler). 20 ist
technisch trivial, aber *verkäuflich schwer* (Software-Firmen
wollen nicht ein Produkt, das ihr eigenes Repo liest —
DSG/DSG-Ansprüchen).

**Akzeptanz:**
- 20 Prototypen (Nr. 1-20) im `prototypes/` Verzeichnis.
- 20 Prototypen mit einem lauffähigen Production-Gate.
- Mindestens 10 mit echtem semantic-Delta (PROD-Orakel-Online).
- CI.yml läuft grün (mit Ollama-Runner für alle 20, oder
  per Conditionals für die ML-schweren).

---

## KENNZAHLEN & EHRLICHKEIT

**Was diese Roadmap IST:**
- 15 Prototypen in 4 Wochen — pro Woche 3-5 Prototypen.
- Jeder Prototyp wird mit dem `gw_proto`-Gate gecheckt
  (kein vorgetauschter GO — nur PROD-online = GO).
- Die `pipeline.py`-Konvention (Katalog-DRY) hält:
  jeder neue Prototyp kostet `manifest.json` + (optional)
  `pipeline.py`, nie einen zweiten Gate-Runner.

**Was diese Roadmap NICHT IST:**
- Kein 20/20 in 4 Wochen mit 0 ML-Evaluation.
- Kein vorgetauschter GO in der oeffentlichen CI.
- Kein 24/7 GPU-Runner für die ML-schweren (Nr. 14-19)
  — falls nicht vorhanden, liefern diese Prototypen
  CONDITIONAL / NO-GO (ehrlich) statt GO.

## KENNZAHLEN AM END-OF-ROADMAP (2026-11-17)

- **10-15 Prototypen** mit lauffähigem Production-Gate
  (je nach ML-Runner-Verfügbarkeit).
- **3-5 Prototypen** mit semantic-Delta in der oeffentlichen
  CI (falls Ollama-Runner aktiv).
- **1 `gw-proto` Meta-Prototyp** (Nr. 0, `prototypes/00-`
  oder `prototypes/20-`) fuer `gw_proto` selbst.
- **6-10 Prototypen** mit fail-loud No-Answer-Cases
  (keine Halluzinationen, kein Halluzinierter Preis,
  kein Halluzinierter Vertrag).

## KENNZAHLEN AM LAUNCH (2026-10-25)

- **1/1** `prototypen` repo public.
- **3/3** RAG-Prototypen (Nr. 1, 4, 6) mit semantic-Delta
  in CI.
- **2/3** (Nr. 1, 6) mit Ollama-Runner (Live GATE in CI,
  falls aktiviert).
- **2/2** deterministic-Prototypen (Nr. 2, 5) mit
  fail-loud cases.
