"""gw_proto — Prototyp-Validation & Production-Gate für GRADweight.

Das ist der "glue, der alles zusammenhält und sichtbar misst, wann ein
Prototyp reif für die Produktion ist — und wann nicht".

Design-Prinzip (genial, nicht mehr Code):
  Ein Prototyp = { ein pipeline.py  +  eine manifest.json  +  Assertions }.
  Der Rest (Eval-Ausführung, Demo-vs-Prod-Orakel, Deltaberechnung,
  GO/NO-GO-Verdict, Reporting) ist hier — einmal geschrieben, für alle
  20 Prototypen wiederverwendet. Das ist der DRY-Core: ein neuer Prototyp
  kostet eine Manifest + 20 Zeilen Pipeline, nie einen neuen Gate-Runner.

Zwei Orakel pro Fall, sichtbar verglichen:
  - DEMO  = StubClient (offline, deterministisch, Wort-Überlapp)
            → was wir JETZT abliefern können, ohne Modell.
  - PROD  = echtes Embedding/Chat-Modell (nomic-embed-text, Ollama/vLLM/
            LiteLLM) → die Produktiv-Performance, falls ein Modell läuft.
  - DELTA = PROD - DEMO pro Metrik. Positiv = Produktion schlägt Demo.

Honesty first (fail-loud):
  Läuft keins PROD-Orakel (kein Modell online), ist das PROD-Resultat
  "pending", und das Verdict wird *nicht* GO-gezählt — es zeigt den
  realen Zustand, statt ein "erfolgreich" vorzutäuschen. Genau das ist
  "wann nicht erfolgreich" — sichtbar, nicht simuliert.
"""
from __future__ import annotations

__version__ = "0.1.0"
