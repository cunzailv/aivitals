# AIVitals · AI Architecture Check

给任意一个 AI 项目做**证据级体检**：架构缺哪层、哪里必然出 bug、对外宣称与代码是否对得上。每条结论都能回溯到 `file:line`。

100% 本地运行，代码不出本机，不训练、不留存。

[![ci](https://github.com/cunzailv/aivitals/actions/workflows/ci.yml/badge.svg)](https://github.com/cunzailv/aivitals/actions/workflows/ci.yml)

```
aivitals scan ./your-ai-project --format md,json,sarif
```

## 它回答四个问题

| 问题 | 怎么答 | 证据 |
|---|---|---|
| 架构缺哪层 | 先识别项目类型与成熟度，再按 17 层核对运行时能力 | 文件 / 配置 / 依赖 |
| 哪里必然出 bug | 查 AI 项目特有的架构级反模式，不是通用 SAST | `file:line` |
| 宣称和实现是否一致 | 声明 → 谓词 → 代码探针 → 四态判定 | 声明原文 + 代码 |
| 先修哪个 | P0/P1 分级 + 单层收敛 + 修法 | 规则 ID |

## 为什么不是又一个「AI 点评器」

1. **规则是资产，LLM 是工具**。24 条规则是结构化 YAML，可执行、可回归、可被 PR 修改；结论必须带证据，无证据直接丢弃。
2. **先画像，再判定**。同一规则在 `prototype` / `internal` / `production` / `multi_tenant` 四档结论不同，报告必须打印按哪档判。
3. **覆盖率不足就不给健康结论**。语言没覆盖、层没跑到、规则不适用，都会写进「覆盖与局限」，不会输出一个假的 `adequate`。

## 安装

```bash
pip install aivitals          # PyPI 发布后可用（当前版本尚未上传）
```

在 PyPI 之前，用三条任一方式安装：

```bash
# 1) 直接装 wheel（不需要 PyPI 账号，也不需要 git）
pip install "https://github.com/cunzailv/aivitals/raw/main/releases/aivitals-0.2.0-py3-none-any.whl"

# 2) 从仓库装
pip install "git+https://github.com/cunzailv/aivitals.git"

# 3) 源码
git clone https://github.com/cunzailv/aivitals.git && cd aivitals && pip install -e .
```

`aivitals --version` 应输出 `aivitals 0.2.0`。

从源码：

```bash
git clone https://github.com/cunzailv/aivitals.git
cd aivitals && pip install -e .
```

## 快速开始

```bash
aivitals checks                                # 列出 24 条规则与 17 层归属
aivitals scan ./repo                           # 默认输出 md + json + sarif
aivitals scan https://github.com/org/repo --out ./aivitals-report
aivitals scan ./repo --doc README.md           # 体检 + 声明对正，合并成一份报告
aivitals claims ./repo --doc README.md         # 只做声明校验
aivitals scan ./repo --baseline .aivitals.json --update-baseline   # 建立基线
aivitals scan ./repo --baseline .aivitals.json                     # 只报新增
aivitals eval --verbose                        # 用标注样例跑召回/误报
aivitals mcp                                   # 以 MCP Server 运行，给 AI 客户端调用
```

`--maturity production` 可覆盖档位；`--fail-on P0` 让 CI 在 P0 时失败（退出码 2）。

## 喂资料：让它越用越准

规则库不是写完就停。把一份架构报告或踩坑清单喂进去：

```bash
aivitals ingest --source ./报告.docx --id geo-2026
```

它会切节、抽候选、标好层与级别，产出 `_draft/geo-2026.candidates.yaml` 待审清单。**候选不参与扫描**，人工补上 `detect` 与 fixture 后才会生效——细节见 [`docs/ingest.md`](docs/ingest.md)。

## 给 AI 用（MCP）

`aivitals mcp` 起一个 stdio MCP Server，四个工具：

| 工具 | 作用 |
|---|---|
| `audit_repo` | 扫描仓库，返回带证据的分级报告 |
| `verify_claims` | 文档宣称 vs 代码实现，四态判定 |
| `list_checks` | 列出规则与层级 |
| `explain_check` | 解释单条规则：后果、改法、依据 |

Claude Desktop / Cursor 的配置见 [`docs/mcp.md`](docs/mcp.md)。

## 放进 CI

GitHub Action（`action.yml`）：

```yaml
- uses: cunzailv/aivitals@main
  with:
    path: .
    fail-on: P0
```

或直接：

```bash
aivitals scan . --fail-on P0 --format md,sarif --out aivitals-report
```

SARIF 可直接上传到 GitHub Code Scanning，PR 里出批注。

## 输出

- `report.md`：按层分组，P0 在最前，含证据、影响、修法
- `report.json`：完整结论 + 画像 + 跳过原因，给 Agent / CI 读；带 `--doc` 时含 `claims`
- `report.sarif`：GitHub Code Scanning / VS Code 直接读，PR 行内批注
- `report.html`：单文件，可直接发给客户

## 当前状态（v0.1.0，诚实版）

已实现：

- 项目画像（类型 / 档位 / 语言 / 依赖 / 入口 / 部署 / 测试 / CI）
- **24 条规则，覆盖全部 17 层**（含 6 条 Go/Java 专用规则）
- 静态检测：regex / 文件存在性 / 依赖 / 组合条件，7 种原语
- 证据链：每条结论附最多 3 条 `file:line`，无证据不进报告
- claim 校验：声明抽取 → 9 条通用谓词 + 3 条 GEO 领域谓词 → 代码探针 → 四态判定
- 四类输出 + 退出码 + 基线（只报新增）
- MCP Server（4 个工具）、GitHub Action、`pytest` 单测（12 个）、CI（3 个 Python 版本）
- eval：4 个标注样例（Python / Go / Java），召回 `19/19`、误报 `0`（样本少，只证明链路成立）

未实现，且**不会假装实现**：

- 覆盖 Python / TypeScript / JavaScript / Go / Java；Rust / Ruby / PHP / Kotlin / C# 仍标注「未纳入检测」
- 无 LLM 语义复核（`--offline` 是唯一模式）
- 英文文档的声明识别率低于中文
- 不做依赖漏洞扫描、不做安全审计

## 规则

规则在 `aivitals/data/checks/*.yaml`，按层分文件。字段与写法见 [`docs/rules.md`](docs/rules.md)，体系与管道见 [`docs/architecture.md`](docs/architecture.md)。

每条规则都带 `derived_from: L{层}/{字段}/{序号}`，指向 17 层体系里的原始条目，避免「规则凭空长出来」。

## 开发

```bash
pip install -e . pytest
python -m pytest -q                        # 单测
aivitals eval --verbose                    # 规则改动门禁（recall ≥ 0.8 且误报 = 0）
aivitals scan fixtures/bad-sync-long-task --out /tmp/r
```

## 边界

- 不做安全审计，不替代渗透测试，不出 CVE 结论
- 不评模型能力、不评技术选型偏好、不评「架构优雅」
- claim 结论只写「未找到证据」或「与实现矛盾」，不做法律定性

## 许可

引擎 Apache-2.0；规则库与 17 层体系 CC-BY-4.0（见 [`LICENSE-CORPUS`](LICENSE-CORPUS)）。
