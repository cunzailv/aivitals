# AIVitals · AI Architecture Check

给任意一个 AI 项目做**证据级体检**：架构缺哪层、哪里必然出 bug、对外宣称与代码是否对得上。每条结论都能回溯到 `file:line`。

100% 本地运行，代码不出本机，不训练、不留存。

```
aivitals scan ./your-ai-project --format md,json,sarif
```

## 它回答四个问题

| 问题 | 怎么答 | 证据 |
|---|---|---|
| 架构缺哪层 | 先识别项目类型与成熟度，再按层核对运行时能力 | 文件/配置/依赖 |
| 哪里必然出 bug | 查 AI 项目特有的架构级反模式，不是通用 SAST | `file:line` |
| 宣称和实现是否一致 | 声明 → 谓词 → 代码探针 → 四态判定 | 声明原文 + 代码 |
| 先修哪个 | P0/P1 分级 + 单层收敛 + 修法 | 规则 ID |

## 为什么不是又一个「AI 点评器」

1. **规则是资产，LLM 是工具**。12 条 P0/P1 规则是结构化 YAML，可执行、可回归、可被 PR 修改；结论必须带证据，无证据直接丢弃。
2. **先画像，再判定**。同一规则在 `prototype` / `internal` / `production` / `multi_tenant` 四档结论不同，报告必须打印按哪档判。
3. **覆盖率不足就不给健康结论**。语言没覆盖、层没跑到、规则不适用，都会写进「覆盖与局限」，不会输出一个假的 `adequate`。

## 快速开始

```bash
pip install -e .
aivitals checks                      # 列出规则
aivitals scan ./repo                 # 默认输出 md + json + sarif
aivitals scan https://github.com/org/repo --out ./aivitals-report
aivitals claims ./repo --doc README.md   # 校验 README 宣称与代码是否一致
aivitals eval --verbose                  # 用标注样例跑召回/误报
```

`--maturity production` 可覆盖档位；`--fail-on P0` 让 CI 在 P0 时失败。

## 输出

- `report.md`：按层分组，P0 在最前，含证据、影响、修法
- `report.json`：完整结论 + 画像 + 跳过原因，给 Agent/CI 读
- `report.sarif`：GitHub Code Scanning / VS Code 直接读，PR 行内批注
- `report.html`：单文件，可直接发给客户

## 当前状态（v0.1，诚实版）

已实现：

- 项目画像（类型 / 档位 / 语言 / 依赖 / 部署）
- 12 条规则（L2/L3/L4/L5/L6/L7/L8/L9/L10/L12/L14/L17）
- 静态检测：regex / 文件存在性 / 依赖 / 组合条件
- claim 校验 v0：声明抽取 → 5 条 core 谓词 → 代码探针 → 四态判定（矛盾/部分/证实/未证）
- 四类输出 + 退出码
- eval：2 个标注样例，`recall 1.000`、健康仓库误报 `0`（样本少，只证明链路成立）

未实现，且**不会假装实现**：

- 只覆盖 Python / TypeScript；Go / Java 等会明确标注「未纳入检测」
- 无 LLM 语义复核（`--offline` 是唯一模式）
- 17 层里目前只有 8 层有规则
- claim 只支持 5 条 core 谓词与中文短语匹配；无 LLM 抽取，英文声明识别率低

## 规则

规则在 `checks/*.yaml`，按层分文件。字段与写法见 [`docs/rules.md`](docs/rules.md)。

每条规则都带 `derived_from: L{层}/{字段}/{序号}`，指向 17 层体系里的原始条目，避免「规则凭空长出来」。

## 开发

```bash
python3 -m aivitals.cli eval --verbose     # 规则改动的门禁
python3 -m aivitals.cli scan fixtures/bad-sync-long-task --out /tmp/r
```

## 边界

- 不做安全审计，不替代渗透测试，不出 CVE 结论
- 不评模型能力、不评技术选型偏好、不评「架构优雅」
- claim 结论只写「未找到证据」或「与实现矛盾」，不做法律定性

## 许可

引擎 Apache-2.0；规则库与 17 层文档 CC-BY-4.0。
