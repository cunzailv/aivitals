"""静态检测执行器：把规则里的 signal 编译成可复核的结论。"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import AuditResult, CheckDef, Evidence, FileInfo, Finding, LayerStatus, Profile
from .rules import MATURITY_ORDER

_GLOB_CACHE: dict[str, re.Pattern] = {}


def glob_to_re(glob: str) -> re.Pattern:
    if glob in _GLOB_CACHE:
        return _GLOB_CACHE[glob]
    i, n, out = 0, len(glob), ""
    while i < n:
        c = glob[i]
        if c == "*":
            if glob[i:i + 3] == "**/":
                out += "(?:.*/)?"
                i += 3
            elif glob[i:i + 2] == "**":
                out += ".*"
                i += 2
            else:
                out += "[^/]*"
                i += 1
        elif c == "?":
            out += "[^/]"
            i += 1
        elif c == "{":
            j = glob.find("}", i)
            if j < 0:
                out += r"\{"
                i += 1
            else:
                parts = [re.escape(p) for p in glob[i + 1:j].split(",")]
                out += "(?:" + "|".join(parts) + ")"
                i = j + 1
        else:
            out += re.escape(c)
            i += 1
    rx = re.compile(out + "$")
    _GLOB_CACHE[glob] = rx
    return rx


def _match(f: FileInfo, globs: list[str]) -> bool:
    return any(glob_to_re(g).match(f.rel) for g in globs)


def _ev(f: FileInfo, lineno: int, text: str) -> Evidence:
    return Evidence(file=f.rel, line=lineno, snippet=text.strip()[:120])


def eval_signal(sig: dict[str, Any], files: list[FileInfo], profile: Profile) -> tuple[str, list[Evidence], str]:
    """返回 (state, evidence, detail)。state ∈ true / false / na。"""
    st = sig.get("type", "")
    globs = list(sig.get("globs") or [])
    pattern = sig.get("pattern") or ""
    max_hits = int(sig.get("max_hits", 3))

    if st in {"regex_any", "regex_count", "none"}:
        rx = re.compile(pattern, re.M | re.I)
        hits: list[Evidence] = []
        count = 0
        for f in files:
            if globs and not _match(f, globs):
                continue
            for i, line in enumerate(f.lines, 1):
                if rx.search(line):
                    count += 1
                    if len(hits) < max_hits:
                        hits.append(_ev(f, i, line))
        if st == "none":
            if count == 0:
                return "true", [], "未发现缓解信号"
            return "false", [], f"发现 {count} 处缓解信号"
        if st == "regex_count":
            need = int(sig.get("min", 1))
            return ("true" if count >= need else "false"), hits, f"命中 {count} 处，阈值 {need}"
        if count == 0:
            return "false", [], "未命中"
        return "true", hits, f"命中 {count} 处"

    if st in {"file_exists", "file_absent"}:
        found = [f for f in files if _match(f, globs)]
        if st == "file_exists":
            if found:
                return "true", [_ev(f, 1, "") for f in found[:max_hits]], f"存在 {len(found)} 个文件"
            return "false", [], "不存在"
        if not found:
            return "true", [Evidence(file="<repo>", line=0, snippet=f"未找到 {globs}")], "不存在（缺失证据）"
        return "false", [], f"存在 {len(found)} 个文件"

    if st in {"dep_any", "dep_none"}:
        names = [n.lower() for n in (sig.get("names") or [])]
        hit = [d for d in profile.deps for n in names if n in d]
        if st == "dep_any":
            if hit:
                return "true", [Evidence(file="<deps>", line=0, snippet=", ".join(hit[:5]))], "依赖命中"
            return "false", [], "依赖未命中"
        if not hit:
            return "true", [Evidence(file="<deps>", line=0, snippet=f"未出现 {names}")], "依赖未出现（缺失证据）"
        return "false", [], "依赖存在"

    return "na", [], f"未知 signal 类型: {st}"


def eval_detect(detect: dict[str, Any], files: list[FileInfo], profile: Profile) -> tuple[str, list[Evidence], str]:
    if "all_of" in detect:
        states = []
        ev: list[Evidence] = []
        details = []
        for s in detect["all_of"]:
            st, e, d = eval_signal(s, files, profile)
            states.append(st)
            ev.extend(e)
            details.append(d)
            if st == "false":
                return "false", ev, "; ".join(details)
        if states and all(x == "true" for x in states):
            return "true", ev, "; ".join(details)
        return "na", ev, "部分信号不适用: " + "; ".join(details)
    if "any_of" in detect:
        ev = []
        details = []
        any_true = False
        has_na = False
        for s in detect["any_of"]:
            st, e, d = eval_signal(s, files, profile)
            details.append(d)
            if st == "true":
                any_true = True
                ev.extend(e)
            if st == "na":
                has_na = True
        if any_true:
            return "true", ev, "; ".join(details)
        return ("na" if has_na else "false"), ev, "; ".join(details)
    st, ev, d = eval_signal(detect, files, profile)
    return st, ev, d


def run_checks(
    profile: Profile,
    files: list[FileInfo],
    checks: list[CheckDef],
    layer_names: dict[int, str] | None = None,
    allow_unchecked: bool = True,
) -> AuditResult:
    findings: list[Finding] = []
    skipped: list[dict[str, str]] = []
    touched_layers: set[int] = set()

    for c in checks:
        if c.applies_to and profile.repo_type not in c.applies_to:
            skipped.append({"check_id": c.id, "reason": f"repo_type={profile.repo_type} 不适用"})
            continue
        if MATURITY_ORDER.get(profile.maturity, 0) < MATURITY_ORDER.get(c.maturity_gate, 0):
            skipped.append({"check_id": c.id, "reason": f"档位 {profile.maturity} 低于门槛 {c.maturity_gate}"})
            continue

        state, ev, detail = eval_detect(c.detect, files, profile)
        if state == "na":
            skipped.append({"check_id": c.id, "reason": f"不适用: {detail}"})
            continue
        touched_layers.add(c.layer)
        if state != "true":
            continue
        if not ev:
            skipped.append({"check_id": c.id, "reason": "命中但无证据，已丢弃"})
            continue

        conf = c.confidence
        if all(e.file.startswith("<") for e in ev):
            conf = "medium"
        findings.append(Finding(
            check_id=c.id, layer=c.layer, group=c.group, title=c.title,
            severity=c.severity, kind=c.kind, confidence=conf, evidence=ev,
            impact=c.impact, fix=c.fix, derived_from=c.derived_from,
        ))

    layers: list[LayerStatus] = []
    for layer in sorted(set(list(touched_layers) + list((layer_names or {}).keys()))):
        fs = [f for f in findings if f.layer == layer]
        if not fs:
            status = "present" if layer in touched_layers else ("unchecked" if allow_unchecked else "not_applicable")
        elif any(f.severity == "P0" for f in fs):
            status = "missing" if any(f.kind == "missing_capability" for f in fs) else "weak"
        else:
            status = "partial"
        layers.append(LayerStatus(layer=layer, name=(layer_names or {}).get(layer, f"L{layer}"), status=status, findings=len(fs)))

    return AuditResult(
        profile=profile,
        findings=sorted(findings, key=lambda f: ({"P0": 0, "P1": 1, "P2": 2, "P3": 3}[f.severity], f.layer)),
        layers=layers,
        skipped=skipped,
        generated_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    )
