"""规则加载与校验。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .model import CheckDef

REQUIRED = ("id", "layer", "title", "severity", "detect")
SEVERITIES = {"P0", "P1", "P2", "P3"}
KINDS = {"defect", "risky_default", "tradeoff", "missing_capability"}
MATURITY_ORDER = {"prototype": 0, "internal": 1, "production": 2, "multi_tenant": 3}


def _to_check(d: dict[str, Any], source: str) -> CheckDef:
    missing = [k for k in REQUIRED if k not in d]
    if missing:
        raise ValueError(f"{source}: 缺少必填字段 {missing}")
    if d["severity"] not in SEVERITIES:
        raise ValueError(f"{source}/{d['id']}: severity 必须是 {SEVERITIES}")
    kind = d.get("kind", "defect")
    if kind not in KINDS:
        raise ValueError(f"{source}/{d['id']}: kind 必须是 {KINDS}")
    gate = d.get("maturity_gate", "prototype")
    if gate not in MATURITY_ORDER:
        raise ValueError(f"{source}/{d['id']}: maturity_gate 未知 {gate}")
    return CheckDef(
        id=str(d["id"]),
        layer=int(d["layer"]),
        group=str(d.get("group", "")),
        title=str(d["title"]),
        severity=d["severity"],
        kind=kind,
        detect=d["detect"],
        fix=str(d.get("fix", "")),
        impact=str(d.get("impact", "")),
        derived_from=str(d.get("derived_from", "")),
        applies_to=list(d.get("applies_to") or []),
        maturity_gate=gate,
        as_of=str(d.get("as_of", "")),
        confidence=str(d.get("confidence", "high")),
        source=source,
    )


def load(checks_dir: Path) -> tuple[list[CheckDef], list[str]]:
    checks: list[CheckDef] = []
    errors: list[str] = []
    if not checks_dir.exists():
        return [], [f"规则目录不存在: {checks_dir}"]
    for path in sorted(checks_dir.glob("*.yaml")) + sorted(checks_dir.glob("*.yml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            errors.append(f"{path.name}: YAML 解析失败 {e}")
            continue
        items = data.get("checks") if isinstance(data, dict) else data
        if not isinstance(items, list):
            errors.append(f"{path.name}: 顶层需要 checks: [...] 列表")
            continue
        for item in items:
            try:
                checks.append(_to_check(item, path.name))
            except (ValueError, TypeError, KeyError) as e:
                errors.append(str(e))
    ids = [c.id for c in checks]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append(f"规则 id 重复: {sorted(dup)}")
    return checks, errors
