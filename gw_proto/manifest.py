"""Manifest: die deklarative Spezifikation eines Prototypen.

Ein manifest.json sagt:
  - id / name
  - corpus        : (optional) Chunk-Liste inline, sonst vom pipeline
  - guard         : ob ein Prompt-Injection-Guard vor der Antwort greift
  - oracles       : wie DEMO und PROD laufen
  - cases         : Testfälle (info / guard_block / no_answer)
  - production_criteria : die Hürden, die ein GO verlangen

JSON statt YAML: stdlib-only, kein python-yaml-Depend (Haus-Stil:
kein pip, kein Netz bei der Validierung).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class Case:
    id: str
    question: str
    expect: str = "info"             # info | guard_block | no_answer
    golden: Optional[str] = None     # erwartete Source (für info)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Case":
        return cls(
            id=d["id"],
            question=d["question"],
            expect=d.get("expect", "info"),
            golden=d.get("golden"),
            tags=list(d.get("tags", []) or []),
        )


@dataclass
class OracleSpec:
    client: str = "stub"             # stub | ollama | remote
    url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    chat_model: str = "llama3.2:3b"
    available: Optional[bool] = None  # nach dem Probe-Call gesetzt

    @classmethod
    def from_dict(cls, d: dict) -> "OracleSpec":
        return cls(
            client=d.get("client", "stub"),
            url=d.get("url", "http://localhost:11434"),
            embed_model=d.get("embed_model", "nomic-embed-text"),
            chat_model=d.get("chat_model", "llama3.2:3b"),
            available=d.get("available"),
        )


@dataclass
class Criterion:
    metric: str                      # recall@3 | guard_blocks | no_false_cite | delta
    oracle: str = "any"              # demo | prod | any
    op: str = ">="
    value: float = 0.0


_OPS = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: abs(a - b) < 1e-9,
    "!=": lambda a, b: abs(a - b) >= 1e-9,
}


@dataclass
class Manifest:
    id: str
    name: str
    corpus: list[dict] = field(default_factory=list)
    guard: bool = True
    min_score_demo: float = 0.12
    min_score_prod: float = 0.30
    oracles: dict[str, Any] = field(default_factory=dict)   # demo/prod -> OracleSpec
    cases: list[Case] = field(default_factory=list)
    criteria: list[Criterion] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "Manifest":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(d)

    @classmethod
    def from_dict(cls, d: dict) -> "Manifest":
        oracles = {}
        for k, v in (d.get("oracles") or {}).items():
            oracles[k] = OracleSpec.from_dict(v)
        if "demo" not in oracles:
            oracles["demo"] = OracleSpec(client="stub")
        if "prod" not in oracles:
            oracles["prod"] = OracleSpec(client="ollama")
        return cls(
            id=d["id"],
            name=d.get("name", d["id"]),
            corpus=list(d.get("corpus") or []),
            guard=bool(d.get("guard", True)),
            min_score_demo=float(d.get("min_score_demo", 0.12)),
            min_score_prod=float(d.get("min_score_prod", 0.30)),
            oracles=oracles,
            cases=[Case.from_dict(c) for c in (d.get("cases") or [])],
            criteria=[
                Criterion(c["metric"], c.get("oracle", "any"),
                          c.get("op", ">="), float(c.get("value", 0.0)))
                for c in (d.get("production_criteria") or [])
            ],
        )

    def info_cases(self) -> list[Case]:
        return [c for c in self.cases if c.expect == "info" and c.golden]

    def info_case_ids(self) -> set[str]:
        return {c.id for c in self.info_cases()}
