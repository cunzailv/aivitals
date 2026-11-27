# AIVitals · 项目计划

> 仓库：<https://github.com/cunzailv/aivitals>（当前为空仓库，main 分支）
> 本计划以我们自己的 17 层体系为主干，GitHub 同类项目只作工程实现参考。
> 版本：v0.1（2026-11-27）

---

## 0. 结论先行

**一句话定位**：给任意一个 AI 项目做「证据级体检」——架构缺哪层、哪里必然出 bug、对外宣称与代码是否对得上，全部结论可回溯到 `file:line`。

**三个决定性取舍**（这三条决定了它不会变成又一个 AI 点评器）：

1. **规则是资产，LLM 是工具**。每条检查项都是可执行、可回归、可被 PR 修改的结构化规则；LLM 只负责规则覆盖不到的语义判断，且不允许产出无证据的结论。
2. **默认离线**。代码不出本机，不做云上传。这条同时消掉了企业最大的采用阻力。
3. **声明对正是差异点**。同赛道已有工具都在查"缺什么模块"，没有一个系统性地查"你说的和做的是不是一回事"。

**首版范围**：12 条 P0 规则 + 3 类输出（JSON/Markdown/SARIF）+ 本地 CLI + 2 个标注样例仓库。不做 250 条全量、不做网页、不做动态 trace。

---

## 1. 定位与差异

| 维度 | 同赛道现状 | AIVitals 的做法 |
|---|---|---|
| 判定方式 | 把 checklist 写进 prompt，让模型自由发挥 | 规则引擎先给确定性结论，LLM 只做补充判定 |
| 证据 | 文字描述"建议检查一下" | 每条结论绑定 Evidence ID，指向 `file:line` / 配置键 / 依赖 / 声明原文 |
| 报告 | 一份 Markdown | SARIF（接 GitHub Code Scanning）+ JSON（接 Agent）+ Markdown（给人）+ 退出码（接 CI） |
| 适配 | 一套标准打所有项目 | 先识别仓库类型与成熟度，再决定跑哪些规则、什么算不合格 |
| 对外表述 | 基本不查 | claim 抽取 → 谓词归一 → 代码探针 → 四态判定 |
| 可信度 | 无度量 | 标注样例集 + 精确率/召回率公示 + 规则变更回归 |

**不做什么**（写进 README，防止预期漂移）：

- 不做安全审计、不替代渗透测试、不出 CVE 结论
- 不评模型能力、不评技术选型偏好、不评"架构优雅"
- 不对"宣称造假"下结论，只输出"未找到证据 / 与实现矛盾"
- 不上传代码、不训练、不留存

---

## 2. 用户与场景

| 用户 | 场景 | 入口 | 关心什么 |
|---|---|---|---|
| 开源作者 / 独立开发者 | 上线前自查、README 夸大自查 | `aivitals scan .` | 哪几条必须先修 |
| 团队 /  Tech Lead | PR 门禁、季度体检 | GitHub Action、`--baseline` | 新增问题不许进主干 |
| 投资 / 采购 / 平台方 | 尽调、接入评估 | 只给 repo URL 或只给简介 | 宣称与实现是否一致、哪些是空壳 |

三者报告口径不同：开发者要"修法"，团队要"增量与阻断"，尽调要"矛盾证据 + 置信度"。同一引擎，三套模板。

---

## 3. 四类能力的规格

### 3.1 架构体检（对应 17 层）

- **输入**：本地仓库路径；或 GitHub URL（本地 `git clone --depth 1` 到临时目录，分析后删除）。
- **前置**：项目画像——仓库类型（`ai_native_app` / `ai_enabled_app` / `ai_infra_or_sdk` / `workflow_framework` / `non_ai_repo`）、成熟度（`prototype` / `internal` / `production` / `multi_tenant`）、主语言、入口、部署方式、依赖清单。
- **判定**：每层给出 `present` / `partial` / `weak` / `missing` / `not_applicable`，只有 `required` 能力缺失才报 `missing`。
- **硬约束**：`non_ai_repo` 直接说明并最小化报告，禁止编造 AI 模块缺口。
- **输出**：层状态矩阵 + 每条结论的证据与修法。

### 3.2 风险倾向（必然出 bug 的模式）

- **定位**：不是 SAST，不查注入/XSS 一类通用漏洞；查"AI 项目特有的、规模一上来必错"的架构级模式。
- **首批模式**（全部静态可查）：外部调用无超时/幂等键、长任务无持久化状态、工具调用无次数与权限上限、上下文无预算、模型调用无 fallback、结构化输出无 schema 校验、记忆并发写无锁、错误被静默吞掉、检索无 rerank 或无权限过滤。
- **输出**：`finding_kind` 区分 `defect`（确定缺陷）/ `risky_default`（危险默认）/ `tradeoff`（设计取舍），防止成熟仓库被误报成"全是缺陷"。

### 3.3 声明对正（差异化能力）

- **输入**：README / 官网文案 / 白皮书 / BP，可单独使用（不给代码也能跑，先出"可疑声明清单"）。
- **三步**：
  1. **抽取**：把自然语言句子抽成可验证声明，并归一为谓词（`multi_tenant`、`data_residency`、`cost_reduction`、`concurrency`、`eval_coverage` 等）。
  2. **探针**：每个谓词配一组代码/配置探针（符号是否存在、取值来源、调用目标域名、是否有压测脚本等）。
  3. **判定**：`confirmed` / `partial` / `unsupported` / `contradicted` 四态。`contradicted` 需 ≥2 条独立证据，否则降级为 `unsupported`。
- **补全**：反向输出"代码里有、简介没写"的能力清单，供作者补文档。
- **措辞**：报告只写"未找到支持该声明的证据"或"实现与该声明矛盾"，不做法律定性。

### 3.4 报告分析

- **分级**：P0（漏钱/漏数据/串租户/上线即事故）→ P1（成本失控、无评测、无 trace）→ P2（可维护性）→ P3（建议）。
- **收敛**：单次报告 P0 不限、P1 最多 10 条、P2 折叠；首次体检只出 Top 10，避免一次 200 条劝退。
- **每条固定字段**：结论 / 证据 / 影响 / 为什么会这样 / 修法 / 置信度 / 规则 ID。
- **不输出总分**：总分会被拿去比较不同项目，改成"层状态 + P0 计数 + 覆盖率"。

---

## 4. 规则体系

### 4.1 从 17 层派生规则的四条通道

页面已有的结构化数据（`corpus/architecture.json`：17 层、62 模块、250 要点）不是文档，而是规则原料。派生规则不需要人肉逐条写：

| 源字段 | 派生为什么 | 检测类型 |
|---|---|---|
| `comps`（层内模块） | 存在性检查：这层的关键能力在运行时是否真实存在 | static + hybrid |
| `decisions`（设计决策） | 断言检查：该有的配置/机制是否到位 | static |
| `pits`（常见坑） | 反模式检查：是否命中已知错误写法 | static（pattern/AST） |
| `check`（一句自检问） | LLM 复核 prompt / 人工问卷项 | llm / manual |

每条规则必须记录 `derived_from: L{层号}/{字段}/{序号}`，保证任何结论都能追回原始体系，而不是凭空长出来。

### 4.2 check 规则 schema（YAML，一文件一条）

```yaml
id: L2-P0-002
layer: 2
group: A
title: 同步接口里跑长任务
severity: P0
kind: defect                 # defect | risky_default | tradeoff
derived_from: L2/pits/1
applies_to: [ai_native_app, ai_enabled_app]
maturity_gate: prototype     # 从哪个成熟度开始报
detect:
  type: static               # static | llm | hybrid | manual
  signals:
    - lang: python
      ast: "route_handler contains await call to agent_run without task_id"
    - glob: "**/{routes,api,views}/**/*.{py,ts}"
      regex: "await\\s+.{0,40}(run_agent|agent\\.invoke|chain\\.ainvoke)"
  negative:                  # 出现以下任一即视为已缓解
    - glob: "**/*.{py,ts}"
      regex: "task_id|job_id|enqueue|celery|arq|bullmq"
evidence:
  required: true
  kinds: [file:line, config_key]
fix: |
  超 30 秒的链路一律异步化：入队 → 返回 task_id → 前端订阅进度。
refs: []
as_of: 2026-11-27
```

字段约束：`severity`、`kind`、`detect.type`、`maturity_gate` 为枚举；`evidence.required` 恒为 true；缺 `derived_from` 的规则不予合并。

### 4.3 档位制（决定"什么叫不合格"）

| 档位 | P0 处理 | P1 处理 | 典型要求 |
|---|---|---|---|
| `prototype` | 全部忽略 | 不到 3 条 | 能跑通即可，不要求评测/多租户 |
| `internal` | 报 | Top 10 | 有幂等、有超时、日志可查 |
| `production` | 阻断 | 全部报 | 有评测集、有 fallback、有成本归属 |
| `multi_tenant` | 阻断 | 阻断成本类 | 租户隔离、key 分离、删除可传导 |

档位来自项目画像，可由用户 `--maturity` 覆盖；报告里必须打印"本次按哪档判定"，否则同一项目换个档位结论全变。

### 4.4 严重度与收敛

- `P0`：会造成资金/数据损失或上线即事故。
- `P1`：不阻断上线，但规模一上来必然出问题。
- `P2` / `P3`：默认折叠在"完整清单"里。
- `baseline`：首次全量结果存为基线，之后只报新增；`--strict` 时连基线内 P0 也报。
- 单层最多 3 条结论（同层多条则合并为一条带子项），避免刷屏。

---

## 5. 引擎与数据流

```
ingest → profile → select → static → (llm) → evidence → score → report → exit
```

| 步 | 做什么 | 失败降级 |
|---|---|---|
| ingest | 本地路径校验 / GitHub 浅克隆到临时目录 | 网络失败 → 提示改用本地路径，不静默 |
| profile | 类型、成熟度、语言、入口、部署、依赖 | 无法分类 → `unclear`，只跑通用规则 |
| select | 按 profile × maturity 选规则子集 | 规则缺失 → 报"覆盖不足"，不假装全查 |
| static | tree-sitter AST + 正则 + 依赖图 + 配置解析 | 语言不支持 → 降级正则并标注低置信度 |
| llm | 仅 hybrid 规则；上下文裁剪到预算内；要求输出 JSON | 无 API key → 跳过并标注"未做语义复核" |
| evidence | 合并、去重、绑定 Evidence ID | 无证据 → 该结论不输出 |
| score | 层状态 + 计数 + 覆盖率 | — |
| report | SARIF / JSON / MD / HTML | — |
| exit | P0 > 0 → 2；P1 > 0 → 1（可配置） | — |

**LLM 调用纪律**：输入只给"画像 + 相关文件片段 + 规则原文"，输出必须是固定 JSON（`verdict` + `evidence_refs` + `reason`）；`evidence_refs` 为空则该条作废。默认 `--offline` 只跑静态。

---

## 6. 报告与接入

**输出**

- `report.sarif`：GitHub Code Scanning / VS Code SARIF Viewer 直接读，PR 上显示行内批注。
- `report.json`：给 Agent 和 CI 读，含 `evidence_index`、`findings`、`claim_checks`、`profile`。
- `report.md`：人读，按层分组，P0 在最前。
- `report.html`：单文件、可分享，适合发给客户/投资人。
- 退出码 + `--fail-on P0`：可直接进 CI 阻断。

**三种接入**

1. `aivitals scan ./repo`——本地，零上传。
2. `aivitals scan https://github.com/org/repo`——浅克隆到临时目录，结束即删。
3. `aivitals mcp`——暴露 `audit_repo`、`explain_check`、`verify_claims` 三个工具，任何支持 MCP 的 IDE/Agent 可直接调。

**隐私承诺**（README 首屏）：仅本地读取；克隆目录在退出时删除；不发任何请求（除显式配置的 LLM provider）；不收集遥测。

---

## 7. 评测与可信度

没有这节，开源后第一条评论就是"AI 瞎评"。

- **fixtures**（10 个，纯手写、可公开）：
  - 5 个"有病"仓库，每个埋 3–5 个已知缺陷（如：同步长任务、单 key 全局、无 eval、进程内状态、无 rerank）。
  - 3 个"健康"仓库（必须 P1 及以上为 0，用于压误报）。
  - 2 个边界仓库（非 AI 项目、极小 demo），验证 `non_ai_repo` 与档位忽略逻辑。
- **指标**：`recall`（埋点被命中比例）、`FPR`（健康仓库误报条数）、`evidence_validity`（证据是否真实指向存在的文件行）。
- **门禁**：规则改动必须跑 `aivitals eval`，`recall ≥ 0.8` 且 `FPR = 0` 才允许合并；指标写进 CI badge 与 README。
- **持续**：每季度用真实开源项目补 fixtures，防止规则只对自家样例有效。

---

## 8. 里程碑

| 里程碑 | 内容 | 验收标准 | 估时 |
|---|---|---|---|
| **M0 骨架** | 关联远程、LICENSE、pyproject、CLI 空跑、SARIF/JSON writer、`corpus/` 落地、README 首屏 | `aivitals scan .` 能输出一份合法 SARIF 且为空结果 | 1–2 天 |
| **M1 规则引擎** | profile + static 执行器 + 12 条 P0 + 2 个 fixture + `eval` 命令 | 在 5 个"有病" fixture 上 recall ≥ 0.8，健康仓库 0 误报 | 3–5 天 |
| **M2 报告闭环** | MD/HTML、退出码、GitHub Action、baseline | 在一个真实开源 AI 项目上跑出可读报告，PR 能显示批注 | 3–4 天 |
| **M3 声明对正** | claim 抽取、谓词库（先 8 个）、探针、四态判定、矛盾证据链 | 对一个 README 宣称"多租户"的项目能给出矛盾证据，或明确 unsupported | 4–6 天 |
| **M4 生态** | MCP server、GitHub URL 接入、规则贡献流程、更多语言、季度复审 | 外部贡献者能只加 YAML 就新增一条规则并通过 eval | 持续 |

**先做 M0–M2 的一个窄切片**：只支持 Python + Docker 两种栈，只跑 12 条 P0 里的 8 条，先证明链路成立。不要一次铺 17 层。

---

## 9. 目录结构

```
aivitals/
├── README.md               # 首屏：定位 / 差异 / 隐私 / 一条命令示例
├── LICENSE                 # Apache-2.0（引擎）
├── LICENSE-CORPUS          # CC-BY-4.0（规则与 17 层文档）
├── pyproject.toml
├── corpus/
│   └── architecture.json   # 17 层结构化数据（已导出）
├── checks/
│   ├── L01-product.yaml
│   ├── L02-delivery.yaml
│   ├── ...
│   └── schema.json         # YAML 校验用 JSON Schema
├── claims/
│   └── predicates.yaml     # 谓词库：multi_tenant / data_residency / ...
├── aivitals/
│   ├── cli.py
│   ├── profile.py
│   ├── ingest.py
│   ├── detect/
│   │   ├── static.py
│   │   ├── ast_rules.py
│   │   └── llm_judge.py
│   ├── claims/
│   │   ├── extract.py
│   │   └── probe.py
│   ├── evidence.py
│   ├── score.py
│   ├── report/
│   │   ├── sarif.py
│   │   ├── markdown.py
│   │   └── html.py
│   └── mcp_server.py
├── fixtures/
│   ├── bad-sync-long-task/
│   ├── bad-single-key/
│   ├── good-production-app/
│   └── expected/*.json      # 标准答案
├── docs/
│   ├── PLAN.md              # 本文件
│   ├── rules.md             # 规则编写指南
│   └── claims.md            # 声明校验方法论
└── .github/workflows/
    ├── eval.yml             # 规则回归门禁
    └── release.yml
```

---

## 10. 开源治理

- **双许可**：引擎 Apache-2.0（商用友好，利于企业接入）；规则库与 17 层文档 CC-BY-4.0（允许转载，要求署名，防止被闭源包装成付费产品）。
- **规则贡献流程**：PR 只改 `checks/*.yaml` + 对应 fixture → CI 自动跑 eval → 维护者审"是否可被证据验证"→ 合并。不接受只写"建议优化"的规则。
- **规则生命周期**：每条带 `as_of`；每季度复审，过期标记 `stale` 并在报告中提示"该规则可能已过时"，而不是继续输出旧结论。
- **版本**：`v0.x` 期间规则 schema 可破坏性变更，必须写迁移说明；`v1.0` 冻结 schema。
- **不做 SaaS**：开源版保持本地运行；若将来做托管服务，必须是独立仓库、独立品牌，避免"开源引流"争议。

---

## 11. 边界与风险

| 风险 | 表现 | 对策 |
|---|---|---|
| 误报 | 健康仓库被报一堆 P1，用户直接弃用 | 档位制 + `finding_kind` + 单层 3 条上限 + 健康 fixture 零误报门禁 |
| LLM 幻觉 | 编出不存在的文件和结论 | 证据必绑；无 `evidence_refs` 作废；默认离线 |
| 规则腐化 | 2026 的规则评 2027 的项目 | `as_of` + 季度复审 + `stale` 标记 |
| 语言覆盖 | 只支持 Python/TS，其他降级 | 显式标注置信度，不假装支持 |
| 法律措辞 | 被判"AI 说我们造假" | 只输出"未找到证据/与实现矛盾"，不做定性，报告首页放免责声明 |
| 维护负担 | 250 条规则无人维护 | 首版只 12 条；规则按层分包，允许社区认领某一层 |

---

## 12. 参考项目吸收表（辅助，不改主干）

| 项目 | 吸收什么 | 不吸收什么 |
|---|---|---|
| `tiezhuli001/ai-architecture-audit` | 仓库类型/成熟度分类枚举、模块矩阵的 `required/expected/optional`、`finding_kind` 三分、`command_ledger`、报告字段命名 | 纯 prompt 驱动、无可执行规则、无 claim 校验、无 SARIF/CI、无精度评测 |
| `semgrep/semgrep` | YAML 规则表达、多语言 pattern、SARIF 输出、CI 集成方式 | 不做通用 SAST/CVE 扫描 |
| `sverweij/dependency-cruiser` | `forbidden`/`allowed` 依赖规则、依赖图可视化 | 只管 JS 依赖 |
| `TNG/ArchUnit`、`import-linter/import-linter` | "架构即测试"的分层契约范式 | JVM / Python-import 限定 |
| `archguard/archguard` | 架构治理的指标视图与规则聚合 | 重型平台，不引入其服务端 |
| `promptfoo/promptfoo` | 断言与评测集的组织方式、CI 报告 | 它评的是模型输出，不评架构 |
| `yamadashy/repomix`、`gitingest` | repo → 单文件上下文的裁剪思路（仅本地实现） | 上传/云端处理 |
| `tree-sitter/tree-sitter` | 多语言 AST，替代正则硬扛 | — |
| `PrefectHQ/fastmcp` | MCP server 暴露方式与工具描述规范 | — |
| `vale-cli/vale` | 文本规则的组织方式（用于 claim 抽取质量校验） | 文档风格检查 |

---

## 附录 A · 首版 12 条 P0（从"十个死法"派生）

| # | 规则 | 层 | 静态信号（示例） |
|---|---|---|---|
| 1 | 同步接口跑长任务 | L2 | 路由 handler 内直接 await Agent，无 `task_id`/队列 |
| 2 | 状态放进程内存 | L5 | 全局 dict / in-memory session，无 redis/db/checkpoint |
| 3 | 业务直连厂商 SDK | L4 | 多处 `openai(...)`/`anthropic(...)`，无 gateway 抽象 |
| 4 | 把 prompt 当权限 | L14 | prompt 含"不要执行 X"，但无工具白名单/参数校验 |
| 5 | 在应用容器跑生成代码 | L10 | `exec`/`eval`/`subprocess` 接用户输入，无沙箱 |
| 6 | 造一个万能工具 | L9 | 单一 shell/SQL 工具直接交给 Agent |
| 7 | 全量上下文硬塞 | L6 | 无 token 预算、无裁剪、无压缩 |
| 8 | 没有评测就上线 | L12 | 无 eval 目录/golden set/回归脚本 |
| 9 | 成本不做归属 | L17 | 无 usage 记录、无 tenant 维度、无预算上限 |
| 10 | 全平台共用一个 key | L3 | 单 key 全局常量，无 per-tenant 分配 |
| 11 | 检索无权限过滤 | L7 | 向量检索前无 tenant/ACL 过滤 |
| 12 | 记忆全量塞向量库 | L8 | 原始对话全量入库，无摘要/去重/淘汰 |

---

## 附录 B · 声明校验示例

```yaml
claim_raw: "支持多租户，数据完全隔离"
predicate: multi_tenant
probes:
  - kind: symbol
    ask: "tenant_id 是否从请求上下文注入"
    expect: "来源为 token/session，而非常量或环境变量"
  - kind: storage
    ask: "向量库/数据库查询是否带 tenant 过滤"
    expect: "query 构造处出现 tenant 条件"
  - kind: key
    ask: "模型调用凭证是否按租户区分"
    expect: "非单一全局 key"
verdict_rules:
  confirmed: 3/3 命中
  partial: 1-2 命中
  contradicted: 出现 ≥2 条反向证据（如 tenant_id 硬编码、查询无过滤）
  unsupported: 仓库中无相关代码可查
report_wording:
  contradicted: "该声明与当前实现矛盾：{evidence}。若为规划中能力，建议在文档标注「计划中」。"
```

---

## 13. 资料注入：怎么越喂越准

### 13.1 四条通道，不能混

同一份资料进错通道，比不进更糟。

| 资料性质 | 典型内容 | 入库形态 | 生效方式 |
|---|---|---|---|
| **规则 / 原则** | 架构文章、踩坑清单、验收标准、评审意见 | `checks/*.yaml` | 静态执行，进 eval 回归 |
| **判据 / 定义** | "什么算多租户"、"什么算成本归属"、"什么叫有评测" | `claims/predicates.yaml` | 生成探针，四态判定 |
| **样例 / 事故** | 有 bug 的仓库、线上事故复盘、别人的审计报告 | `fixtures/` + `expected/*.json` | 提升 recall、压误报 |
| **表述 / 宣传** | 产品简介、官网文案、BP、白皮书 | `corpus/sources/claims/` | claim 抽取语料 |

一份资料常常同时含两类（比如事故复盘里既有规则也有样例），`ingest` 要允许拆开分别入不同通道，而不是整份丢进去。

### 13.2 ingest 流水线

```
aivitals ingest <path|url> [--kind rule|case|claim|doc]
```

1. **落地原文**：存到 `corpus/sources/{YYYYMMDD}-{slug}/`，记录 `sha256`、来源 URL、抓取时间、原始格式。原文永不改写，只做引用。
2. **抽取候选**（LLM）：按 `--kind` 输出候选——规则候选（含检测信号草案）、谓词候选（含探针草案）、声明候选、反模式候选。抽取结果写进 `checks/_draft/`，**不直接生效**。
3. **人工确认**：`aivitals review` 逐条 accept / reject / edit。规则必须能回答"用什么证据证明"，答不上来的直接拒。
4. **晋升**：通过后进入 `checks/` 或合并进已有规则；谓词进 `claims/predicates.yaml`；样例进 `fixtures/` 并写 `expected/`。
5. **回归**：新规则必须跑 `aivitals eval`，健康 fixture 零误报才允许合并。

### 13.3 直接复用你已有的记忆四层

这套机制不需要另造，正好对应你画过的四层结构：

| 记忆层 | 在本项目里的位置 | 收敛动作 |
|---|---|---|
| L1 原始日志 | `corpus/sources/` 原文 | 只读、可回查 |
| L2 零碎笔记 | `checks/_draft/` 候选 | 人审后淘汰/合并 |
| L3 结构化手册 | `checks/`、`claims/predicates.yaml` | `aivitals compact` 去重、补 `derived_from` |
| L4 预加载上下文 | 判定时按画像加载的规则子集 | 不全量塞 prompt |

`compact` 就是这里的 Dreaming：把重复规则合并、把 `as_of` 过期的标 stale、把没有出处的候选清掉。

### 13.4 三条防污染红线

1. **`source_ref` 必填**：每条规则、每个谓词都要指回原文的具体段落。指不回去的不进库——否则半年后没人知道这条规则凭什么存在。
2. **冲突不覆盖**：新资料与旧规则矛盾时，标 `conflict` 并保留双方 + 各自 `as_of`，由人裁决。架构领域本来就有对立观点（该用 Agent 还是 Workflow），覆盖式更新会把体系越改越薄。
3. **只有过 eval 才晋升**：未经回归的规则只能停在 `_draft/`。否则规则库会被"看起来很有道理"的观点稀释。

### 13.5 为什么不做自动学习

自动吸收的代价是：结果不可复现、结论不可解释、回归无法定位。开源工具最怕"同一仓库跑两次结论不同"。所以这里的定位是**人工确认 + 自动执行**，不是自动学习。LLM 负责把资料读成候选，人负责决定它算不算规则，引擎负责每次都一样地执行。

---

## 下一步

M0 只做四件事：接远程、`corpus/` 入库、CLI 空跑出合法 SARIF、README 首屏写完。完成后再进 M1 的规则引擎，避免先写一堆文档再发现跑不起来。
