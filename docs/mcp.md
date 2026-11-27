# 接入 AI 客户端（MCP）

AIVitals 自带一个 stdio MCP Server，任何支持 MCP 的客户端（Claude Desktop、Cursor、Cline、自研 Agent）都能直接调用体检能力，不需要模型自己去读一堆文件猜。

```bash
aivitals mcp
```

## 四个工具

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `audit_repo` | 扫描仓库，返回带证据的分级报告 | `path`（绝对路径）、`maturity`（可选覆盖档位） |
| `verify_claims` | 文档宣称 vs 代码实现，四态判定 | `path`、`doc`（默认 `README.md`） |
| `list_checks` | 列出 18 条内置规则与 17 层归属 | — |
| `explain_check` | 解释一条规则：后果、改法、依据 | `id`，如 `L02-P0-001` |

返回内容都是 markdown 文本，模型可以直接转述，也可以作为下一步修改的输入。

## Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "aivitals": {
      "command": "aivitals",
      "args": ["mcp"]
    }
  }
}
```

如果没有全局安装，用绝对路径：

```json
{
  "mcpServers": {
    "aivitals": {
      "command": "python3",
      "args": ["-m", "aivitals.cli", "mcp"],
      "env": { "PYTHONPATH": "/path/to/aivitals" }
    }
  }
}
```

## Cursor

`.cursor/mcp.json` 同上结构。改完重启客户端，在工具列表里应能看到 `aivitals` 的四个工具。

## 手动验证

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n' | aivitals mcp
```

第一条应返回 `protocolVersion`，第二条应返回 4 个工具。

## 边界

- MCP Server **只读**：不写文件、不装依赖、不执行被扫描仓库的代码。
- `audit_repo` 的路径必须是本机可读目录；传 URL 请先在本地 clone（扫描器不会替客户端拉代码）。
- 报告里的「未找到证据」只表示没在代码里找到实现，不构成法律或合规结论。
