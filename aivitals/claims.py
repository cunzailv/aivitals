"""声明对正：从文档抽 claim → 归一谓词 → 代码探针 → 四态判定。

判定原则：
- contradicted 需要 ≥1 条硬反证且正向证据不足，或 ≥2 条硬反证；
- 只有正向证据全中才 confirmed；
- 找不到任何相关代码时是 unsupported，不是「没问题」。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import detect
from .model import Evidence, FileInfo, Profile

VERDICTS = ("confirmed", "partial", "unsupported", "contradicted")


@dataclass
class Claim:
    text: str
    line: int
    predicate_id: str
    predicate_title: str


@dataclass
class ClaimResult:
    claim: Claim
    verdict: str
    positive: list[tuple[str, str]] = field(default_factory=list)   # (ask, detail)
    negative: list[tuple[str, str]] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim.text,
            "doc_line": self.claim.line,
            "predicate": self.claim.predicate_id,
            "predicate_title": self.claim.predicate_title,
            "verdict": self.verdict,
            "evidence": [{"file": e.file, "line": e.line, "snippet": e.snippet} for e in self.evidence],
            "positive": self.positive,
            "negative": self.negative,
            "note": self.note,
        }


def load_predicates(path: Path) -> tuple[list[dict[str, Any], list[str]]]:
    if not path.exists():
        return [], [f"谓词库不存在: {path}"]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return [], [f"谓词库解析失败: {e}"]
    items = data.get("predicates") or []
    errs = [f"谓词缺少 id/claim_patterns/probes: {p.get('id')}" for p in items
            if not (p.get("id") and p.get("claim_patterns") and p.get("probes"))]
    return items, errs


def split_claims(text: str, min_len: int = 6, max_len: int = 180) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith(("#", "|", "```", ">", "---")):
            continue
        s = re.sub(r"^[-*+]\s+|^\d+\.\s+|^\[\s*\]\s*", "", s)
        for part in re.split(r"[。；;！!？?]", s):
            part = part.strip(" ，,、:：")
            if min_len <= len(part) <= max_len:
                out.append((i, part))
    return out


def extract(text: str, predicates: list[dict[str, Any]], per_predicate: int = 2) -> list[Claim]:
    claims: list[Claim] = []
    seen: dict[str, int] = {}
    for line, sent in split_claims(text):
        for p in predicates:
            if seen.get(p["id"], 0) >= per_predicate:
                continue
            if any(pat in sent for pat in p["claim_patterns"]):
                claims.append(Claim(sent, line, p["id"], p.get("title", p["id"])))
                seen[p["id"]] = seen.get(p["id"], 0) + 1
                break
    return claims


def _run_probes(probes: list[dict[str, Any]], files: list[FileInfo], profile: Profile):
    hits, details, ev = 0, [], []
    for pr in probes:
        st, e, d = detect.eval_signal(pr, files, profile)
        ask = pr.get("ask", "")
        details.append((ask, d))
        if st == "true":
            hits += 1
            ev.extend(e)
    return hits, len(probes), details, ev


def verify(claim: Claim, pred: dict[str, Any], files: list[FileInfo], profile: Profile) -> ClaimResult:
    probes = pred.get("probes") or {}
    pos_hits, pos_total, pos_details, ev = _run_probes(probes.get("positive") or [], files, profile)
    neg_hits, neg_total, neg_details, neg_ev = _run_probes(probes.get("negative") or [], files, profile)

    res = ClaimResult(claim=claim, verdict="unsupported", positive=pos_details, negative=neg_details,
                      evidence=ev + neg_ev)

    if pos_total == 0:
        res.note = "谓词没有正向探针，无法校验"
        return res
    if neg_total and neg_hits >= 2:
        res.verdict = "contradicted"
        res.note = pred.get("on_contradicted") or "存在多处反向证据"
        return res
    if neg_total and neg_hits >= 1 and pos_hits == 0:
        res.verdict = "contradicted"
        res.note = pred.get("on_contradicted") or "存在反向证据，且没有任何正向实现"
        return res
    if neg_total and neg_hits == 1 and pos_hits > 0:
        res.verdict = "partial"
        res.note = "能力存在，但发现一处反向疑点，建议人工核查"
        return res
    if pos_hits == pos_total:
        res.verdict = "confirmed"
        res.note = "代码中找到了完整实现证据"
        return res
    if pos_hits > 0:
        res.verdict = "partial"
        res.note = f"{pos_hits}/{pos_total} 个探针命中，能力存在但不完整"
        return res
    res.verdict = "unsupported"
    res.note = "仓库中没有找到与该声明相关的实现，可能是规划中能力或纯文档项目"
    return res


def run(root: Path, doc: Path, files: list[FileInfo], profile: Profile,
        predicates: list[dict[str, Any]]) -> list[ClaimResult]:
    text = doc.read_text(encoding="utf-8", errors="ignore")
    claims = extract(text, predicates)
    by_id = {p["id"]: p for p in predicates}
    return [verify(c, by_id[c.predicate_id], files, profile) for c in claims]


def to_markdown(results: list[ClaimResult], doc: Path) -> str:
    if not results:
        return f"## 声明校验\n\n在 `{doc}` 中没有识别到可校验的声明。\n"
    order = {"contradicted": 0, "partial": 1, "confirmed": 2, "unsupported": 3}
    label = {"contradicted": "矛盾", "partial": "部分支撑", "confirmed": "已证实", "unsupported": "未找到证据"}
    lines = ["## 声明校验", "",
             f"文档：`{doc}` · 识别 {len(results)} 条可校验声明", "",
             "| 声明 | 谓词 | 结论 | 依据 |", "|---|---|---|---|"]
    for r in sorted(results, key=lambda x: order[x.verdict]):
        basis = r.note
        if r.evidence:
            e = r.evidence[0]
            basis = f"`{e.file}:{e.line}`" + (f" {e.snippet[:40]}" if e.snippet else "")
        lines.append(f"| {r.claim.text[:40]} | {r.claim.predicate_title} | **{label[r.verdict]}** | {basis} |")
    lines += ["", "> 「未找到证据」不等于「没有实现」；「矛盾」只表示当前代码与该声明不一致。", ""]
    return "\n".join(lines)
