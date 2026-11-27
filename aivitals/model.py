"""数据模型：仓库画像、证据、结论。"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class FileInfo:
    rel: str
    ext: str
    lines: list[str]
    size: int


@dataclass
class Evidence:
    file: str
    line: int
    snippet: str = ""

    def key(self) -> str:
        return f"{self.file}:{self.line}"


@dataclass
class Profile:
    root: str
    repo_type: str = "unclear"          # ai_native_app | ai_enabled_app | ai_infra_or_sdk | non_ai_repo | unclear
    maturity: str = "prototype"         # prototype | internal | production | multi_tenant
    languages: dict[str, int] = field(default_factory=dict)
    file_count: int = 0
    loc: int = 0
    ai_signals: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)
    entrypoints: list[str] = field(default_factory=list)
    deployment: list[str] = field(default_factory=list)
    has_tests: bool = False
    has_ci: bool = False
    covered_languages: list[str] = field(default_factory=list)
    uncovered_languages: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    check_id: str
    layer: int
    group: str
    title: str
    severity: str                      # P0 | P1 | P2 | P3
    kind: str                          # defect | risky_default | tradeoff
    confidence: str                    # high | medium | low
    evidence: list[Evidence]
    impact: str = ""
    fix: str = ""
    derived_from: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "layer": self.layer,
            "group": self.group,
            "title": self.title,
            "severity": self.severity,
            "kind": self.kind,
            "confidence": self.confidence,
            "evidence": [asdict(e) for e in self.evidence],
            "impact": self.impact,
            "fix": self.fix,
            "derived_from": self.derived_from,
        }


@dataclass
class CheckDef:
    id: str
    layer: int
    group: str
    title: str
    severity: str
    kind: str
    detect: dict[str, Any]
    fix: str = ""
    impact: str = ""
    derived_from: str = ""
    applies_to: list[str] = field(default_factory=list)
    maturity_gate: str = "prototype"
    as_of: str = ""
    confidence: str = "high"
    source: str = ""


@dataclass
class LayerStatus:
    layer: int
    name: str
    status: str                        # present | partial | weak | missing | not_applicable
    findings: int = 0


@dataclass
class AuditResult:
    profile: Profile
    findings: list[Finding]
    layers: list[LayerStatus]
    skipped: list[dict[str, str]] = field(default_factory=list)
    suppressed: list[Finding] = field(default_factory=list)
    generated_at: str = ""
    version: str = "0.1.0"

    @property
    def p0(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "P0"]

    @property
    def p1(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "P1"]
