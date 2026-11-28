"""智能体、技能、工作流三种资产的读取与导出。

都是纯文本，跟着包一起安装；`aivitals export` 可一键铺到项目里
（Claude Code 用 .claude/agents 与 .claude/skills，其它工具自行指定目录）。
"""
from __future__ import annotations

import re
from pathlib import Path

KINDS = ("agents", "skills", "workflows")
DEFAULT_DEST = {
    "agents": ".claude/agents",
    "skills": ".claude/skills",
    "workflows": ".aivitals/workflows",
}


def parse_frontmatter(text: str) -> dict:
    meta: dict[str, str] = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return meta
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta


def items(data_dir: Path, kind: str) -> list[dict]:
    if kind == "agents":
        files = sorted((data_dir / "agents").glob("*.md"))
    elif kind == "skills":
        files = sorted((data_dir / "skills").glob("*/SKILL.md"))
    elif kind == "workflows":
        files = sorted((data_dir / "workflows").glob("*.yaml"))
    else:
        raise ValueError(f"未知类型：{kind}")
    out = []
    for p in files:
        if kind == "workflows":
            text = p.read_text(encoding="utf-8")
            name = p.stem
            desc = ""
            for line in text.splitlines():
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                    break
        else:
            text = p.read_text(encoding="utf-8")
            meta = parse_frontmatter(text)
            name = meta.get("name") or (p.parent.name if kind == "skills" else p.stem)
            desc = meta.get("description", "")
        out.append({"name": name, "description": desc, "path": str(p), "kind": kind})
    return out


def show(data_dir: Path, kind: str, name: str) -> str:
    for item in items(data_dir, kind):
        if item["name"] == name:
            return Path(item["path"]).read_text(encoding="utf-8")
    raise KeyError(f"没有 {kind} 资产：{name}")


def export(data_dir: Path, kind: str, dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for item in items(data_dir, kind):
        src = Path(item["path"])
        if kind == "skills":
            target = dest / src.parent.name / "SKILL.md"
            target.parent.mkdir(parents=True, exist_ok=True)
        else:
            target = dest / src.name
        target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        written.append(target)
    return written
