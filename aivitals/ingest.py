"""资料入账：把外部文档切成节，抽成候选规则，等人工晋升。

不是「AI 读一遍就自动生成规则」——那会产生一堆无法验证的噪音。
这里做的是把资料变成**可评审的结构化候选**：每句都带回指到章节，
层与级别只是提示，真正生效前必须人工补 detect 与 fixture。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import yaml

LAYER_HINTS: list[tuple[str, int]] = [
    (r"租户|多租户|tenant|隔离", 3),
    (r"配额|限额|quota|预算上限|budget", 3),
    (r"网关|模型路由|fallback|gateway|路由", 4),
    (r"重试|幂等|超时|异步|队列|retry|idempot", 2),
    (r"上下文|context|压缩|截断|窗口", 6),
    (r"检索|RAG|向量|召回|rerank|知识库", 7),
    (r"记忆|memory|偏好|历史", 8),
    (r"工具|tool|function call|MCP|插件", 9),
    (r"沙箱|代码执行|exec|sandbox|执行环境", 10),
    (r"多智能体|handoff|supervisor|协作|调度", 11),
    (r"评测|评估|回归|标注|golden|eval", 12),
    (r"可观测|日志|trace|监控|observability|埋点", 13),
    (r"权限|越权|注入|安全|RBAC|鉴权", 14),
    (r"控制面|后台|配置|console|admin|运营", 15),
    (r"部署|容器|docker|k8s|基础设施|发布", 16),
    (r"成本|计费|账单|cost|用量", 17),
    (r"场景|需求|验收|用户|价值", 1),
]

SIGNAL = re.compile(
    r"(必须|禁止|不要|避免|否则|会导致|风险|失败|坑|注意|务必|应当|应该|需要|"
    r"不能|无法|缺|漏|丢|崩溃|失控|不可|"
    r"should|must|never|fail|risk|avoid|require|missing)",
    re.I,
)
HARD = re.compile(r"(必须|禁止|绝不|never|must|否则)", re.I)
SOFT = re.compile(r"(建议|注意|可以考虑|should|consider)", re.I)

HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*$")


class _HTMLToMarkdown(HTMLParser):
    """极简 HTML→文本：保留 h1-h4 作为 markdown 标题，其余按段落落行。"""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._h: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag in {"h1", "h2", "h3", "h4"}:
            self._h = "#" * int(tag[1])
        elif tag in {"p", "div", "section", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"h1", "h2", "h3", "h4"}:
            self._h = None
            self.parts.append("\n")
        elif tag in {"p", "div", "section", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self._h:
            self.parts.append(f"\n\n{self._h} {text}\n")
        else:
            self.parts.append(text)

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def read_source(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".html" or suffix == ".htm":
        parser = _HTMLToMarkdown()
        parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
        return parser.text()
    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        try:
            import docx  # type: ignore
        except ImportError:
            raise SystemExit("读取 .docx 需要 python-docx：pip install python-docx；或先另存为 md/txt")
        d = docx.Document(str(path))
        lines: list[str] = []
        for para in d.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style = (para.style.name or "").lower()
            if style.startswith("heading"):
                level = int(re.sub(r"\D", "", style) or 1)
                lines.append("#" * min(level, 4) + " " + text)
            else:
                lines.append(text)
        for table in d.tables:
            for row in table.rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                joined = " · ".join(c for c in cells if c)
                if joined:
                    lines.append(joined)
        return "\n\n".join(lines)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            raise SystemExit("读取 .pdf 需要 pypdf：pip install pypdf；或先导出为 md/txt")
        reader = PdfReader(str(path))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    raise SystemExit(f"不支持的格式：{suffix}（支持 md / txt / html / docx / pdf）")


def split_sections(text: str) -> list[dict]:
    sections: list[dict] = []
    title = "（正文）"
    buf: list[str] = []
    for line in text.splitlines():
        m = HEADING.match(line)
        if m:
            if buf:
                sections.append({"title": title, "body": "\n".join(buf).strip()})
            title = m.group(2)
            buf = []
        else:
            buf.append(line)
    if buf:
        sections.append({"title": title, "body": "\n".join(buf).strip()})
    return [s for s in sections if s["body"]]


def _sentences(body: str) -> list[str]:
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    chunks: list[str] = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith(">"):
            continue
        if s.startswith("|"):
            for cell in s.strip("|").split("|"):
                c = cell.strip()
                if c and not re.fullmatch(r"[-: ]+", c):
                    chunks.append(c)
            continue
        if len(s) <= 220:
            chunks.append(s)
            continue
        chunks.extend(re.split(r"(?<=[。！？；])|(?<=，)", s))
    out: list[str] = []
    for c in chunks:
        c = c.strip(" -•*·\t")
        if 10 <= len(c) <= 220:
            out.append(c)
    return out


def _layer(text: str) -> int:
    """取命中位置最靠前的那个层，避免「检索按租户过滤」被判成租户层。"""
    best, best_pos = 0, 10 ** 9
    for pattern, layer in LAYER_HINTS:
        m = re.search(pattern, text, re.I)
        if m and m.start() < best_pos:
            best, best_pos = layer, m.start()
    return best


def _severity(text: str) -> str:
    if HARD.search(text):
        return "P0"
    if SOFT.search(text):
        return "P2"
    return "P1"


def build_candidates(sections: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for sec in sections:
        for sent in _sentences(sec["body"]):
            if len(sent) < 10 or len(sent) > 220:
                continue
            if not SIGNAL.search(sent):
                continue
            digest = hashlib.sha1(sent.encode("utf-8")).hexdigest()[:8]
            if digest in seen:
                continue
            seen.add(digest)
            out.append({
                "id": f"CAND-{digest}",
                "layer_hint": _layer(f"{sec['title']} {sent}"),
                "severity_hint": _severity(sent),
                "section": sec["title"],
                "text": sent,
                "detect": "待人工转写：拆成 globs + pattern + 必须缺失的反证",
            })
    return out


def ingest(source: Path, corpus_id: str, root: Path, draft_dir: Path, keep_source: bool = True) -> dict:
    text = read_source(source)
    if not text.strip():
        raise SystemExit("资料为空，或无法抽取文本")
    sections = split_sections(text)
    candidates = build_candidates(sections)

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    source_dir = root / "corpus" / "sources" / corpus_id
    if keep_source:
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "canonical.md").write_text(text, encoding="utf-8")
        (source_dir / "sections.json").write_text(
            json.dumps({"id": corpus_id, "sections": sections}, ensure_ascii=False, indent=1), encoding="utf-8")
        (source_dir / "manifest.json").write_text(json.dumps({
            "id": corpus_id,
            "origin": str(source),
            "sha256": sha,
            "chars": len(text),
            "sections": len(sections),
            "publishable": False,
            "note": "原始资料不进公开仓库；只有改写后的规则可发布",
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    draft_dir.mkdir(parents=True, exist_ok=True)
    draft = draft_dir / f"{corpus_id}.candidates.yaml"
    draft.write_text(yaml.dump({
        "source": corpus_id,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "note": "候选规则不参与扫描；晋升需人工补 detect、impact、fix、derived_from 与 fixture",
        "candidates": candidates,
    }, allow_unicode=True, sort_keys=False, default_flow_style=False), encoding="utf-8")

    by_layer: dict[int, int] = {}
    for c in candidates:
        by_layer[c["layer_hint"]] = by_layer.get(c["layer_hint"], 0) + 1

    return {
        "id": corpus_id,
        "chars": len(text),
        "sections": len(sections),
        "candidates": len(candidates),
        "by_layer": dict(sorted(by_layer.items())),
        "draft": str(draft),
        "source_dir": str(source_dir) if keep_source else "",
    }
