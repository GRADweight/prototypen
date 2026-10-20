"""RAG-Chatbot über gw-shared-lib — smoke-demo (offline, kein Netz).

Nutzt die 6 Bausteine von gw-shared-lib: RAGPipeline + GuardPipeline
+ Chunk + Guard + Config + Audit. Lauffähig ohne Setup.

Für Produktion: setze GW_INFER_URL + GW_INFER_EMBED (nomic-embed-text
über Ollama). Ohne: der StubClient (bag-of-words) reicht für
Retrieval-Logik, aber nicht für echte Semantik.
"""
from __future__ import annotations
import sys
import pathlib

# shared-lib einbinden (Relativ-Pfad, kein pip nötig für die Demo)
sys.path.insert(
    0,
    str(pathlib.Path(__file__).resolve().parents[4] / "shared-lib"),
)

from gw_shared_lib import RAGPipeline, GuardPipeline, Chunk  # noqa: E402

# Minimal-Korpus (synthetisch, kein Kundendaten)
CORPUS = [
    Chunk(content="Ferientage im 1. Dienstjahr: 25 Tage. Ab 50: 28 Tage.",
          source="reglement/urlaub.md#3.1", confidence=0.84,
          access_level="internal"),
    Chunk(content="Krankheitsanzeige: innerhalb 3 Tage, ab 4. Tag ärztliches Attest.",
          source="reglement/urlaub.md#4.2", confidence=0.72,
          access_level="internal"),
    Chunk(content="Gehaltstabellen sind konfidenciell und werden protokolliert.",
          source="hr/gehalts.md#1", confidence=0.9,
          access_level="confidential"),
]


def main() -> int:
    q = sys.argv[1] if len(sys.argv) > 1 else \
        "Wie viele Ferientage habe ich im ersten Dienstjahr?"
    pipe = RAGPipeline(corpus=CORPUS, guard=GuardPipeline(), use_stub=True)
    res = pipe.answer(q)

    print("\nFrage:    " + q)
    print("Antwort:  " + res.answer)
    for i, c in enumerate(res.citations, 1):
        print("  [%d] %s (Conf: %.2f, Retrieval: %.3f)" % (
            i, c["source"], c["confidence"], c["retrieval_score"]))
    if res.guard_blocked:
        print("  [GUARD] Blockiert: " + res.guard_reason)

    ok = bool(res.citations) and not res.guard_blocked
    print("\nSTATUS: " + ("OK" if ok else "KEIN TREFFER"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
