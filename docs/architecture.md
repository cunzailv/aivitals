# 架构说明

## 一句话

**规则是资产，工具只做取证；模型只当裁判，不当证人。**

AIVitals 不靠 LLM 读代码瞎猜，而是用可审计的规则命中「结构 + 证据」，再由人或模型在证据基础上判断。

## 17 层 → 4 组

体系把 AI 项目拆成 17 层，按产品交付链路分成 4 组：

| 组 | 层 | 关心的问题 |
|---|---|---|
| A 入口与身份 | L1 产品场景、L2 接入交付、L3 身份租户配额、L4 模型网关 | 谁来用、怎么接、谁的额度、走哪个模型 |
| B 运行时 | L5 编排运行时、L6 上下文工程、L7 检索与知识、L8 记忆、L9 工具与动作、L10 代码执行、L11 多智能体 | 一次任务怎么跑起来、跑挂了怎么办 |
| C 结果与可信 | L12 评测、L13 可观测、L14 安全与权限 | 怎么知道它答得对、出错能不能查、会不会越权 |
| D 商业与交付 | L15 控制面、L16 基础设施、L17 成本 | 能不能规模化交付、账单清不清楚 |

完整数据在 `aivitals/data/architecture.json`（每层含 role / comps / decisions / pits / check / 参考项目）。

## 规则从哪来

每条规则必须能指回体系里的一个具体字段，四种派生通道：

| 来源 | 变成了什么规则 |
|---|---|
| `comps`（该层应有哪些组件） | 存在性规则：`file_absent` / `dep_none` |
| `decisions`（必须做的技术决策） | 断言规则：有 A 无 B 就是缺口 |
| `pits`（该层典型死法） | 反模式规则：`regex_any` + `none` 组合 |
| `check`（验收清单） | 需要 LLM 或人工复核的部分，不进静态规则 |

规则文件每条都带 `derived_from`（如 `L2/pits/2`），评审时可以回到体系原文核对，不是拍脑袋加的。

## 引擎管道

```
ingest（本地路径 / GitHub URL 浅克隆）
  → profile（类型、档位、语言、依赖、AI 信号、入口、部署）
  → gate（按档位过滤：prototype 只跑 P0，production 才跑 production 门槛规则）
  → detect（原语求值：regex_any / regex_count / none / file_exists / file_absent / dep_any / dep_none，组合 all_of / any_of）
  → evidence（每条结论附最多 3 条 file:line，无证据直接丢弃并记 skipped）
  → layer status（present / partial / weak / missing / unchecked）
  → overall（critical_gaps / weak / unsupported_language / adequate / insufficient_coverage）
  → report（json / markdown / SARIF 2.1.0 / 单文件 HTML）
```

### 为什么先画像

同一个写法在原型和线上是两回事。`maturity` 决定规则是否生效：

- prototype：只拦会当场卡死的（同步长任务、进程内状态）
- internal：加身份、网关、编排类
- production：加检索权限、评测、prompt 当权限
- multi_tenant：加租户隔离、审计、成本归属

画像还负责诚实：只覆盖 python / typescript / javascript 时，Go、Java 项目会明确标 `unsupported_language` 并列出未覆盖语言，而不是给一个假的「健康」。

## 声明对正

`verify_claims` 不做关键词匹配就下结论，而是四态：

| 态 | 含义 | 允许出现在报告里吗 |
|---|---|---|
| `confirmed` | 找到实现证据，且与声明一致 | 是 |
| `partial` | 找到部分实现，缺关键约束（如硬编码 `tenant_id="default"`） | 是 |
| `contradicted` | 代码与声明矛盾（如 README 说校验 schema，代码直接 `json.loads`） | 是，且必须带证据 |
| `unsupported` | 没找到证据 | 是，但措辞只能是「未找到证据」 |

谓词库在 `aivitals/data/claims/predicates.yaml`（5 条通用）与 `predicates.geo.yaml`（8 条 GEO 领域）。每条谓词带 `scope` 和 `acceptance_ref`，指回原始验收清单的章节锚点。

## 目录

```
aivitals/
  data/
    architecture.json      # 17 层体系
    checks/L*.yaml         # 18 条规则，按层分文件
    claims/*.yaml          # 谓词库
  model.py                 # 数据结构
  profile.py               # 仓库画像
  rules.py                 # 规则加载与校验
  detect.py                # 原语求值与证据
  claims.py                # 声明四态
  report.py                # 四种输出
  mcp_server.py            # MCP stdio server
  cli.py                   # scan / claims / checks / eval / mcp
fixtures/                  # 标注样例（评测用）
examples/                  # 真实输出样例
```

## 不做什么

- 不做安全审计（不替代 SAST）
- 不做依赖漏洞扫描
- 不给「这个项目能上线」的结论
- 不把「没找到证据」写成「没实现」
