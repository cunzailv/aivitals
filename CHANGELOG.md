# Changelog

## v0.2.1 — 2026-11-28

### 给 AI 的提示词

- 新增 `aivitals prompt --for audit|claims|fix|ci [--lang en] [--copy]`，直接打印可粘贴给 AI 的整段提示词
- README 增加「复制给 AI」一节：不开终端，粘一段就能让 AI 自己装、自己扫、按证据汇报
- `docs/prompts.md` 收录五套模板与「为什么这样写」
- 提示词内置安装命令与版本号、写死四态口径（`unsupported` 只能说「未找到证据」）、禁止批量改代码
- 免账号分发：`releases/` 内置 0.2.0/0.2.1 的 wheel 与 sdist，raw 链接可直接 `pip install`

## v0.2.0 — 2026-11-27

### 更聪明

- **资料入账**：`aivitals ingest` 把 md / txt / html / docx / pdf 切成节、抽候选、标层与级别。一份 1 万字报告实测出 27 条候选（41 节），原文与候选都不进公开仓库。
- **Go / Java 覆盖**：新增 6 条语言专用规则（Go handler 同步跑模型、Go 全局 map 会话、Java static Map 缓存、Go/Java 直接执行生成代码等），语言覆盖从 3 种到 5 种。
- **覆盖率改为从规则反推**：`languages_covered` 扫描规则里真实出现的扩展名，不再靠声明。原来声称支持 JavaScript 但规则只扫 `.ts`，这次补齐 `.js/.tsx/.jsx`。
- **画像修正**：`go.mod` / `pom.xml` 参与依赖解析；Go `_test.go`、Java `*Test.java` 计入测试；Go HTTP 与 Spring 注解计入 Web 特征。

### 验证

- 4 个标注样例（Python ×2、Go、Java）：召回 19/19，误报 0
- 17 个单元测试全过（新增 5 个 ingest 测试）

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
