# Changelog

## v0.1.0 — 2026-11-27

首个可用版本：能 clone 下来直接跑，能出报告，能被 AI 客户端调用。

### 引擎

- 仓库画像：类型 / 档位 / 语言 / 依赖 / AI 信号 / 入口 / 部署 / 测试 / CI，跳过 `.git`、`node_modules`、`.venv` 等
- 7 种检测原语：`regex_any`、`regex_count`、`none`、`file_exists`、`file_absent`、`dep_any`、`dep_none`，支持 `all_of` / `any_of`
- 证据：每条结论附最多 3 条 `file:line`，取不到证据不进报告
- 档位门槛：prototype / internal / production / multi_tenant 四档，按画像自动判定并可 `--maturity` 覆盖
- 诚实降级：语言未覆盖时输出 `unsupported_language` 并列出未覆盖语言

### 规则

- 18 条规则，覆盖全部 17 层（P0 7 条、P1 8 条、P2 1 条、P3 2 条）
- 每条带 `derived_from` 指回体系字段、`impact`、`fix`
- 评测门禁：`aivitals eval` 在 bad fixture 上 13/13 召回，good fixture 上 0 误报

### 声明对正

- 四态判定：confirmed / partial / contradicted / unsupported
- 9 条通用谓词 + 3 条 GEO 领域谓词
- `scan --doc README.md` 可把声明校验并入主报告

### 输出与接入

- 四种输出：JSON、Markdown、SARIF 2.1.0、单文件 HTML
- `--fail-on P0` 可直接做 CI 门禁；`--baseline` 只报新增问题
- MCP stdio server：`audit_repo` / `verify_claims` / `list_checks` / `explain_check`
- GitHub Action（`action.yml`）+ 自带 CI（3 个 Python 版本 × 单测 × eval × 扫描 × MCP 冒烟）

### 已知限制

- 只覆盖 python / typescript / javascript
- 规则是结构性的，不替代安全审计与依赖漏洞扫描
- 英文文档的声明识别率低于中文
