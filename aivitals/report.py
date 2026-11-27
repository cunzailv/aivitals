"""输出：JSON / Markdown / SARIF / 单文件 HTML。"""
from __future__ import annotations

import html as _html
import json
from typing import Any

from .model import AuditResult, Evidence, Finding

SEV_TO_SARIF = {"P0": "error", "P1": "warning", "P2": "note", "P3": "note"}
SEV_LABEL = {"P0": "P0 · 必须修", "P1": "P1 · 应尽快修", "P2": "P2 · 可排期", "P3": "P3 · 建议"}


def _ev_text(e: Evidence) -> str:
    if e.line <= 0:
        return e.snippet or e.file
    return f"`{e.file}:{e.line}` — {e.snippet}"


def summary(r: AuditResult) -> dict[str, Any]:
    allf = list(r.findings) + list(r.suppressed)
    p0 = sum(1 for f in allf if f.severity == "P0")
    p1 = sum(1 for f in allf if f.severity == "P1")
    checked = [l for l in r.layers if l.status != "unchecked"]
    return {
        "p0": p0,
        "p1": p1,
        "p2": sum(1 for f in allf if f.severity == "P2"),
        "p3": sum(1 for f in allf if f.severity == "P3"),
        "baseline_suppressed": len(r.suppressed),
        "layers_checked": len(checked),
        "layers_total": 17,
        "coverage": round(len(checked) / 17, 2),
        "covered_languages": r.profile.covered_languages,
        "uncovered_languages": r.profile.uncovered_languages,
        "overall": ("critical_gaps" if p0 else
                    ("weak" if p1 else
                     ("unsupported_language" if (r.profile.uncovered_languages and not checked) else
                      ("adequate" if len(checked) >= 10 else "insufficient_coverage")))),
        "exit_level": (2 if p0 else (1 if p1 else 0)),
    }


def to_json(r: AuditResult) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "tool": {"name": "aivitals", "version": r.version},
        "generated_at": r.generated_at,
        "disclaimer": "架构体征不等于安全审计，不能替代渗透测试；claim 结论仅表示未找到证据或与实现矛盾。",
        "summary": summary(r),
        "profile": r.profile.to_dict(),
        "layers": [l.__dict__ for l in r.layers],
        "findings": [f.to_dict() for f in r.findings],
        "skipped": r.skipped,
    }


def to_sarif(r: AuditResult) -> dict[str, Any]:
    rules = []
    for f in sorted({f.check_id: f for f in r.findings}.values(), key=lambda x: x.check_id):
        rules.append({
            "id": f.check_id,
            "name": f.title.replace(" ", "_"),
            "shortDescription": {"text": f.title},
            "fullDescription": {"text": f.impact or f.title},
            "help": {"text": f.fix or "见规则库", "markdown": f.fix or "见规则库"},
            "properties": {"severity": f.severity, "layer": f.layer, "kind": f.kind, "tags": ["ai-architecture", f"L{f.layer}"]},
        })
    results = []
    for f in r.findings:
        locs = []
        for e in f.evidence:
            if e.line > 0 and not e.file.startswith("<"):
                locs.append({"physicalLocation": {
                    "artifactLocation": {"uri": e.file},
                    "region": {"startLine": e.line, "snippet": {"text": e.snippet}},
                }})
        item: dict[str, Any] = {
            "ruleId": f.check_id,
            "level": SEV_TO_SARIF.get(f.severity, "note"),
            "message": {"text": f"{f.title}｜{f.impact}" if f.impact else f.title},
            "properties": {"severity": f.severity, "confidence": f.confidence, "layer": f.layer},
        }
        if locs:
            item["locations"] = locs
        results.append(item)
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {"driver": {
                "name": "aivitals", "version": r.version, "informationUri": "https://github.com/cunzailv/aivitals",
                "rules": rules,
            }},
            "results": results,
        }],
    }


def to_markdown(r: AuditResult, max_p1: int = 10, per_layer: int = 3) -> str:
    s = summary(r)
    p = r.profile
    lines = [
        "# AI 项目体征报告",
        "",
        f"**仓库** `{p.root}`",
        "",
        f"| 项目类型 | 成熟度档位 | 主语言 | 文件数 | 代码行 |",
        f"|---|---|---|---|---|",
        f"| {p.repo_type} | {p.maturity} | {', '.join(list(p.languages)[:3]) or '-'} | {p.file_count} | {p.loc} |",
        "",
        f"**结论**：P0 {s['p0']} 条，P1 {s['p1']} 条；已检查 {s['layers_checked']} 层（共 17 层），总体 `{s['overall']}`。",
        "",
        "> 架构体征不等于安全审计；claim 结论仅表示「未找到证据」或「与实现矛盾」。",
        "",
    ]
    if r.suppressed:
        lines.insert(len(lines) - 1,
            f"> 基线已抑制 {len(r.suppressed)} 条既有问题（不计入下方新增列表，但仍计入总分）。")
    unchecked = [l for l in r.layers if l.status == "unchecked"]
    gate_skips = [x for x in r.skipped if "档位" in x["reason"]]
    locs = []
    if unchecked:
        locs.append("- 未覆盖层：" + "、".join(f"L{l.layer} {l.name}" for l in unchecked))
    if gate_skips:
        gs = sorted({int(x["check_id"][1:3]) for x in gate_skips if x["check_id"][1:3].isdigit()})
        locs.append("- 因档位门槛未执行：" + "、".join(f"L{g}" for g in gs) + f"（当前档位 {p.maturity}）")
    if p.uncovered_languages:
        locs.append("- 检测器语言覆盖：" + ("、".join(p.covered_languages) or "无") + "；本仓库存在 " + "、".join(p.uncovered_languages) + "，相关代码未纳入检测")
    if locs:
        lines += ["## 覆盖与局限", ""] + locs + [""]
    if not r.findings:
        lines += ["## 结论详情", "", "本次未发现 P0/P1 级架构缺陷。", ""]
    for sev in ("P0", "P1", "P2", "P3"):
        group = [f for f in r.findings if f.severity == sev]
        if not group:
            continue
        shown, total = group, len(group)
        if sev == "P1":
            shown = group[:max_p1]
        kept, per = [], {}
        for f in shown:
            per[f.layer] = per.get(f.layer, 0) + 1
            if per[f.layer] <= per_layer:
                kept.append(f)
        lines += [f"## {SEV_LABEL[sev]}（{total} 条）", ""]
        for f in kept:
            layer = next((l.name for l in r.layers if l.layer == f.layer), f"L{f.layer}")
            lines += [f"### {f.title}", "", f"`{f.check_id}` · L{f.layer} {layer} · {f.kind} · 置信度 {f.confidence}", ""]
            if f.impact:
                lines += [f"**影响**：{f.impact}", ""]
            lines += ["**证据**：", ""]
            for e in f.evidence[:3]:
                lines += [f"- {_ev_text(e)}"]
            lines += [""]
            if f.fix:
                lines += [f"**修法**：{f.fix}", ""]
            if f.derived_from:
                lines += [f"<sub>来源 {f.derived_from}</sub>", ""]
        if len(kept) < total:
            lines += [f"> 本段折叠了 {total - len(kept)} 条（单层最多 {per_layer} 条），完整清单见 `report.json`。", ""]
    if r.layers:
        lines += ["## 层状态", "", "| 层 | 名称 | 状态 | 结论数 |", "|---|---|---|---|"]
        for l in r.layers:
            lines += [f"| L{l.layer} | {l.name} | {l.status} | {l.findings} |"]
        lines += [""]
    if r.skipped:
        lines += ["## 未执行的检查", "", "| 规则 | 原因 |", "|---|---|"]
        for s2 in r.skipped[:20]:
            lines += [f"| {s2['check_id']} | {s2['reason']} |"]
        if len(r.skipped) > 20:
            lines += [f"| … | 另有 {len(r.skipped) - 20} 条 |"]
        lines += [""]
    lines += ["---", f"生成于 {r.generated_at} · aivitals v{r.version}"]
    return "\n".join(lines)


def to_html(r: AuditResult) -> str:
    s = summary(r)
    p = r.profile
    color = {"P0": "#b42318", "P1": "#b54708", "P2": "#475467", "P3": "#667085"}
    cards = []
    for f in r.findings:
        ev = "".join(f"<li><code>{_html.escape(_ev_text(e))}</code></li>" for e in f.evidence[:3])
        cards.append(
            f'<div class="card"><div class="row"><span class="sev" style="color:{color.get(f.severity,"#475467")}">'
            f'{f.severity}</span><span class="cid">{_html.escape(f.check_id)}</span>'
            f'<span class="layer">L{f.layer}</span></div>'
            f'<h3>{_html.escape(f.title)}</h3>'
            f'<ul>{ev}</ul>'
            f'<p class="fix">{_html.escape(f.fix)}</p></div>'
        )
    layers = "".join(f"<tr><td>L{l.layer}</td><td>{_html.escape(l.name)}</td><td>{l.status}</td><td>{l.findings}</td></tr>" for l in r.layers)
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>AI 项目体征报告</title><style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f7f7f5;color:#1a1a1a;margin:0;padding:40px}}
.wrap{{max-width:900px;margin:0 auto}}h1{{font-size:26px;margin:0 0 8px}}
.meta{{color:#667085;font-size:13px;margin-bottom:24px}}
.sum{{display:flex;gap:12px;margin:20px 0 28px}}.kpi{{background:#fff;border:1px solid #e4e4e7;border-radius:10px;padding:14px 18px;min-width:110px}}
.kpi b{{display:block;font-size:22px}}.kpi span{{font-size:12px;color:#667085}}
.card{{background:#fff;border:1px solid #e4e4e7;border-radius:10px;padding:16px 18px;margin:12px 0}}
.row{{display:flex;gap:10px;align-items:center;font-size:12px}}.sev{{font-weight:700}}.cid{{color:#667085}}.layer{{color:#98a2b3}}
h3{{font-size:15px;margin:8px 0}}.card ul{{margin:6px 0;padding-left:18px}}.card li{{font-size:13px;color:#344054}}
.fix{{font-size:13px;color:#475467;background:#f9fafb;padding:8px 10px;border-radius:6px}}
table{{width:100%;border-collapse:collapse;background:#fff;font-size:13px}}td,th{{border:1px solid #e4e4e7;padding:6px 10px;text-align:left}}
.note{{font-size:12px;color:#98a2b3;margin-top:24px}}
</style></head><body><div class="wrap">
<h1>AI 项目体征报告</h1>
<div class="meta">{_html.escape(p.root)} · {p.repo_type} · 档位 {p.maturity} · {p.file_count} 文件 / {p.loc} 行</div>
<div class="sum"><div class="kpi"><b style="color:{color['P0']}">{s['p0']}</b><span>P0 必须修</span></div>
<div class="kpi"><b style="color:{color['P1']}">{s['p1']}</b><span>P1 应尽快修</span></div>
<div class="kpi"><b>{s['layers_checked']}/17</b><span>已检查层</span></div>
<div class="kpi"><b>{s['overall']}</b><span>总体</span></div></div>
<h2 style="font-size:16px">结论</h2>{''.join(cards)}
<h2 style="font-size:16px;margin-top:28px">层状态</h2>
<table><tr><th>层</th><th>名称</th><th>状态</th><th>结论数</th></tr>{layers}</table>
<div class="note">架构体征不等于安全审计；claim 结论仅表示未找到证据或与实现矛盾。生成于 {r.generated_at} · aivitals v{r.version}</div>
</div></body></html>"""
