"""gw_proto CLI — `python -m gw_proto <manifest.json> [options]`

Der ein-zu-ein Command, mit dem ein Prototyp seinen Production-Gate
läuft. Erzeugt:
  - die sichtbare Gate-Report (Stdout, auch lesbar)
  - ein JSON-Verdict (artifacts/<proto>/verdict.json — CI-Artefakt,
    im PR-Log + als diff-Tracking im Zeitverlauf)
  - einen Exit-Code (0 = GO/CONDITIONAL, 1 = NO-GO, 2 = Fehler)

Das ist der "glue": jeder der 20 Prototypen ruft denselben Einpunkt,
läuft denselben Gate, vergleicht denselben DELTA. Ein neuer Prototyp
bringt also KEINEN neuen Runner mit — nur ein Manifest + eine 20-Zeilen-
pipeline.py für die nicht-RAG-Fälle.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .manifest import Manifest
from .runner import run_manifest
from .gate import evaluate, write_verdict, render_report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gw-proto",
                                 description="Run a GRADweight prototype through its production gate.")
    ap.add_argument("manifest", help="path to a prototype manifest.json")
    ap.add_argument("--root", default=".",
                    help="repo root (parent of prototypes/, vendor/, gw_proto/)")
    ap.add_argument("--artifact", default=None,
                    help="output path for the JSON verdict (default: artifacts/<id>/verdict.json)")
    ap.add_argument("--no-prod", action="store_true",
                    help="do not probe a live model (demo-only run)")
    ap.add_argument("--audit", default=None,
                    help="audit log path (append JSONL; default: .audit/gate.jsonl)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if (root / "vendor") not in [Path(p) for p in sys.path]:
        sys.path.insert(0, str(root / "vendor"))

    manifest = Manifest.load(args.manifest)
    audit_path = Path(args.audit) if args.audit else (root / ".audit" / "gate.jsonl")

    metrics = run_manifest(manifest, root=root,
                          audit_path=audit_path, probe=not args.no_prod)
    verdict = evaluate(metrics, manifest)

    print(render_report(metrics, verdict))

    out = Path(args.artifact) if args.artifact else (root / "artifacts" / manifest.id / "verdict.json")
    write_verdict(verdict, out)
    print(f"\n  → JSON verdict written to {out}")
    print(f"  → audit entries appended to {audit_path}")

    if verdict.overall == "GO":
        return 0
    if verdict.overall == "CONDITIONAL":
        return 0      # conditional is a valid, honest state (not a failure)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
