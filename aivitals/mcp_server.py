"""AIVitals MCP Server（stdio）。

让 Claude Desktop / Cursor / 任意 MCP 客户端直接调用体检能力：
  - audit_repo      扫描仓库，返回带证据的分级报告
  - verify_claims   校验 README/文档里的宣称与代码是否对得上
  - list_checks     列出全部规则
  - explain_check   解释单条规则的依据与改法

协议：JSON-RPC 2.0，一行一条消息，stdin/stdout。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import claims as claims_mod, detect, profile as prof, report, rules

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "aivitals"
SERVER_VERSION = "0.2.0"

TOOLS = [
    {
        "name": "audit_repo",
        "description": "扫描一个 AI 项目的架构体征，返回按 P0-P3 分级、每条带文件行号证据的报告。只读，不上传代码。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "本地仓库绝对路径"},
                "maturity": {"type": "string", "enum": ["prototype", "internal", "production", "multi_tenant"],
                             "description": "覆盖档位判定；不传则自动推断"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "verify_claims",
        "description": "把项目文档里的宣称（多租户、幂等、校验、审计、成本归属等）与代码对照，输出 confirmed/partial/contradicted/unsupported 四态。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "本地仓库绝对路径"},
                "doc": {"type": "string", "description": "相对仓库的文档路径，默认 README.md"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_checks",
        "description": "列出内置规则（17 层体系），含 id、层级、级别、档位门槛。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "explain_check",
        "description": "解释一条规则：为什么这是问题、会造成什么后果、怎么改、依据来自哪一层。",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "规则 id，如 L02-P0-001"}},
            "required": ["id"],
        },
    },
]

_LAYERS: dict[int, str] = {}


def _layers(checks_dir: Path) -> dict[int, str]:
    global _LAYERS
    if _LAYERS:
        return _LAYERS
    corpus = checks_dir.parent / "architecture.json"
    try:
        data = json.loads(corpus.read_text(encoding="utf-8"))
        _LAYERS = {int(l["id"]): l["name"] for l in data.get("LAYERS", [])}
    except (OSError, ValueError, KeyError):
        _LAYERS = {}
    return _LAYERS


def _load(checks_dir: Path):
    checks, errs = rules.load(checks_dir)
    if not checks:
        raise RuntimeError("没有可用规则：" + "; ".join(errs))
    return checks


def _audit(path: str, maturity: str | None, checks_dir: Path) -> str:
    root = Path(path).expanduser()
    if not root.exists():
        return f"路径不存在：{root}"
    checks = _load(checks_dir)
    profile, files = prof.build(root, rules.languages_covered(checks))
    if maturity:
        profile.maturity = maturity
    result = detect.run_checks(profile, files, checks, _layers(checks_dir))
    return report.to_markdown(result)


def _verify(path: str, doc: str, checks_dir: Path) -> str:
    root = Path(path).expanduser()
    if not root.exists():
        return f"路径不存在：{root}"
    doc_path = Path(doc)
    if not doc_path.is_absolute():
        doc_path = root / doc_path
    if not doc_path.exists():
        return f"文档不存在：{doc_path}"
    profile, files = prof.build(root)
    preds, errs = claims_mod.load_predicates(checks_dir.parent / "claims" / "predicates.yaml")
    if not preds:
        return "谓词库为空：" + "; ".join(errs)
    results = claims_mod.run(root, doc_path, files, profile, preds)
    return claims_mod.to_markdown(results, doc_path)


def _list(checks_dir: Path) -> str:
    checks = _load(checks_dir)
    lines = [f"共 {len(checks)} 条规则", ""]
    for c in checks:
        layer = _layers(checks_dir).get(c.layer, f"L{c.layer}")
        lines.append(f"- `{c.id}` L{c.layer} {layer} · {c.severity} · {c.title}（门槛 {c.maturity_gate}）")
    return "\n".join(lines)


def _explain(check_id: str, checks_dir: Path) -> str:
    checks = _load(checks_dir)
    for c in checks:
        if c.id == check_id:
            layer = _layers(checks_dir).get(c.layer, f"L{c.layer}")
            return "\n".join([
                f"# {c.id} · {c.title}",
                "",
                f"- 层级：L{c.layer} {layer}",
                f"- 级别：{c.severity}（类型 {c.kind}）",
                f"- 档位门槛：{c.maturity_gate}",
                f"- 依据：{c.derived_from}",
                "",
                "## 为什么会出问题",
                c.impact,
                "",
                "## 怎么改",
                c.fix,
            ])
    return f"没有找到规则 {check_id}"


def _call(name: str, args: dict, checks_dir: Path) -> str:
    if name == "audit_repo":
        return _audit(args["path"], args.get("maturity"), checks_dir)
    if name == "verify_claims":
        return _verify(args["path"], args.get("doc", "README.md"), checks_dir)
    if name == "list_checks":
        return _list(checks_dir)
    if name == "explain_check":
        return _explain(args["id"], checks_dir)
    raise ValueError(f"未知工具：{name}")


def _handle(req: dict, checks_dir: Path) -> dict:
    method = req.get("method")
    rid = req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }}
    if method in ("notifications/initialized", "initialized"):
        return {}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            text = _call(name, args, checks_dir)
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": text}],
                "isError": False,
            }}
        except Exception as e:  # noqa: BLE001 面向客户端的错误必须回传而不是崩溃
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],
                "isError": True,
            }}
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": f"Method not found: {method}"}}


def serve(checks_dir: Path) -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            print(json.dumps({"jsonrpc": "2.0", "id": None,
                              "error": {"code": -32700, "message": f"Parse error: {e}"}}), flush=True)
            continue
        if isinstance(req, list):
            out = [r for r in (_handle(x, checks_dir) for x in req) if r]
            print(json.dumps(out, ensure_ascii=False), flush=True)
            continue
        resp = _handle(req, checks_dir)
        if resp:
            print(json.dumps(resp, ensure_ascii=False), flush=True)
    return 0
