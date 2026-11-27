"""仓库画像：类型、成熟度、语言、依赖、部署方式。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .model import FileInfo, Profile

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "dist", "build", "__pycache__",
    ".idea", ".vscode", ".next", "target", "vendor", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "coverage", "htmlcov", ".tox", "site-packages",
}
SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".tar",
    ".mp4", ".mov", ".mp3", ".wav", ".woff", ".woff2", ".ttf", ".so", ".dylib",
    ".pyc", ".lock", ".min.js", ".map", ".key", ".pem", ".crt",
}
LANG_MAP = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
    ".jsx": "javascript", ".go": "go", ".java": "java", ".rs": "rust", ".rb": "ruby",
    ".php": "php", ".cs": "csharp", ".kt": "kotlin", ".swift": "swift",
}
AI_PKGS = [
    "openai", "anthropic", "langchain", "langgraph", "llama-index", "llama_index",
    "litellm", "dify", "coze", "ollama", "vllm", "mcp", "chromadb", "pinecone",
    "qdrant", "milvus", "faiss", "weaviate", "pgvector", "sentence-transformers",
    "transformers", "huggingface", "tiktoken", "vercel/ai", "@anthropic-ai/sdk",
]
WEB_PKGS = [
    "fastapi", "flask", "django", "starlette", "uvicorn", "tornado",
    "next", "nuxt", "express", "koa", "nest", "hono", "trpc",
]
MAX_FILES = 5000
MAX_BYTES = 512 * 1024


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def walk(root: Path) -> list[FileInfo]:
    out: list[FileInfo] = []
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and (not d.startswith(".") or d == ".github")]
        for name in filenames:
            if len(out) >= MAX_FILES:
                return out
            p = Path(dirpath) / name
            ext = p.suffix.lower()
            if ext in SKIP_EXT or name.endswith(".min.js") or name.endswith(".min.css"):
                continue
            try:
                if p.stat().st_size > MAX_BYTES:
                    continue
            except OSError:
                continue
            if ext not in LANG_MAP and ext not in {".md", ".toml", ".yaml", ".yml", ".json", ".txt", ".cfg", ".ini", ".sql", ".dockerfile"} and not name.startswith("Dockerfile"):
                continue
            text = _read_text(p)
            if not text:
                continue
            out.append(FileInfo(rel=str(p.relative_to(root)), ext=ext or name, lines=text.splitlines(), size=len(text)))
    return out


def _deps_from(root: Path, files: list[FileInfo]) -> list[str]:
    deps: set[str] = set()
    for f in files:
        p = root / f.rel
        if f.rel.endswith("requirements.txt"):
            for line in f.lines:
                s = line.strip()
                if not s or s.startswith("#") or s.startswith("-"):
                    continue
                m = re.match(r"^([A-Za-z0-9_.\-]+)", s)
                if m:
                    deps.add(m.group(1).lower().replace("_", "-"))
        elif f.rel.endswith("pyproject.toml"):
            txt = "\n".join(f.lines)
            for m in re.finditer(r'"([A-Za-z0-9_.\-]+)[<>=!~\[ ]', txt):
                deps.add(m.group(1).lower().replace("_", "-"))
            for m in re.finditer(r"^\s*([A-Za-z0-9_.\-]+)\s*=", txt, re.M):
                deps.add(m.group(1).lower().replace("_", "-"))
        elif f.rel.endswith("package.json"):
            try:
                data = json.loads("\n".join(f.lines))
            except json.JSONDecodeError:
                continue
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                for k in (data.get(key) or {}):
                    deps.add(k.lower())
        elif f.rel.endswith("go.mod"):
            for m in re.finditer(r"^\s+(?:require\s+)?([a-zA-Z0-9_.\-/]+)\s+v", "\n".join(f.lines), re.M):
                deps.add(m.group(1).lower())
    return sorted(deps)


def _ai_signals(deps: list[str], files: list[FileInfo]) -> list[str]:
    hits: set[str] = set()
    for d in deps:
        for pkg in AI_PKGS:
            if pkg in d:
                hits.add(pkg)
    joined = "\n".join("\n".join(f.lines[:200]) for f in files if f.ext in {".py", ".ts", ".js", ".go"} and not f.rel.startswith("corpus/"))
    for pkg in AI_PKGS:
        token = pkg.replace("-", "_")
        if re.search(rf"\b(import|from|require|import\()\s*[^\n]*{re.escape(token)}", joined, re.I):
            hits.add(pkg)
    return sorted(hits)


def _maturity(files: list[FileInfo], deps: list[str], text_all: str) -> str:
    has_docker = any(f.rel.startswith("Dockerfile") or f.rel.endswith("docker-compose.yml") or f.rel.endswith("docker-compose.yaml") for f in files)
    has_ci = any(".github/workflows/" in f.rel or f.rel.endswith(".gitlab-ci.yml") for f in files)
    has_tests = any(re.search(r"(^|/)(tests?|__tests__|spec)/", f.rel) or f.rel.endswith(("_test.py", ".test.ts", ".spec.ts")) for f in files)
    tenant_hits = len(re.findall(r"tenant_id|tenantId|tenant_id\b", text_all))
    multi = tenant_hits >= 3
    if multi:
        return "multi_tenant"
    if has_docker and (has_tests or has_ci):
        return "production"
    if has_docker or has_tests:
        return "internal"
    return "prototype"


def build(root: Path) -> tuple[Profile, list[FileInfo]]:
    files = walk(root)
    deps = _deps_from(root, files)
    langs: dict[str, int] = {}
    loc = 0
    for f in files:
        lang = LANG_MAP.get(f.ext)
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
            loc += len(f.lines)

    text_all = "\n".join("\n".join(f.lines) for f in files if f.ext in LANG_MAP)
    ai = _ai_signals(deps, files)
    maturity = _maturity(files, deps, text_all)

    entrypoints = [f.rel for f in files if f.rel in {"main.py", "app.py", "src/main.py", "src/index.ts", "src/main.ts", "manage.py", "server.py"}]
    for f in files:
        if f.rel.endswith("package.json"):
            try:
                data = json.loads("\n".join(f.lines))
            except json.JSONDecodeError:
                continue
            main = data.get("main")
            if main:
                entrypoints.append(f"{f.rel}:{main}")
    deployment = [f.rel for f in files if f.rel.startswith("Dockerfile") or "docker-compose" in f.rel or f.rel.endswith(".gitlab-ci.yml")]

    web = any(d in WEB_PKGS or any(w in d for w in WEB_PKGS) for d in deps) or bool(
        re.search(r"(from\s+fastapi|import\s+fastapi|FastAPI\(|from\s+flask|Flask\(|@app\.(get|post)|express\(|NextRequest)", text_all)
    )
    gatewayish = any(k in text_all.lower() for k in ("gateway", "fallback", "upstream", "model router", "load balance"))
    if ai and gatewayish and not web:
        repo_type = "ai_infra_or_sdk"
    elif ai and web:
        repo_type = "ai_native_app"
    elif ai:
        repo_type = "ai_enabled_app" if web else "ai_infra_or_sdk"
    elif web:
        repo_type = "non_ai_repo"
    else:
        repo_type = "unclear"

    COVERED = {"python", "typescript", "javascript"}
    covered = sorted(l for l in langs if l in COVERED)
    uncovered = sorted(l for l in langs if l not in COVERED)

    prof = Profile(
        root=str(root),
        repo_type=repo_type,
        maturity=maturity,
        languages=dict(sorted(langs.items(), key=lambda kv: -kv[1])),
        file_count=len(files),
        loc=loc,
        ai_signals=ai,
        deps=deps[:80],
        entrypoints=sorted(set(entrypoints)),
        deployment=deployment,
        has_tests=any(re.search(r"(^|/)(tests?|__tests__|spec)/", f.rel) for f in files),
        has_ci=any(".github/workflows/" in f.rel for f in files),
        covered_languages=covered,
        uncovered_languages=uncovered,
    )
    if not files:
        prof.notes.append("空目录或无可读源文件")
    if prof.file_count >= MAX_FILES:
        prof.notes.append("文件数达到扫描上限，结果可能不完整")
    return prof, files
