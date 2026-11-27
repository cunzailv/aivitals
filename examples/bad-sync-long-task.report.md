# AI 项目体征报告

**仓库** `fixtures/bad-sync-long-task`

| 项目类型 | 成熟度档位 | 主语言 | 文件数 | 代码行 |
|---|---|---|---|---|
| ai_native_app | production | python | 10 | 37 |

**结论**：P0 7 条，P1 6 条；已检查 17 层（共 17 层），总体 `critical_gaps`。

> 架构体征不等于安全审计；claim 结论仅表示「未找到证据」或「与实现矛盾」。

## P0 · 必须修（7 条）

### 同步接口里跑长任务

`L02-P0-001` · L2 接入与交付层 · defect · 置信度 high

**影响**：网关先超时，用户以为卡死，后台还在烧 token。

**证据**：

- `app.py:16` — result = await chain.ainvoke({"input": payload["q"]})

**修法**：超过 30 秒的链路一律异步化：入队 → 立刻返回 task_id → 前端订阅进度。

<sub>来源 L2/pits/1</sub>

### 全平台共用一个模型 key

`L03-P0-002` · L3 身份、租户与配额层 · risky_default · 置信度 high

**影响**：泄露一次等于全损，且无法定位是谁烧的。

**证据**：

- `app.py:9` — OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
- `app.py:10` — llm = ChatOpenAI(api_key=OPENAI_API_KEY)

**修法**：key 按租户或按用途拆分，最小权限 + 定期轮换，泄露只影响一个租户。

<sub>来源 L3/pits/1</sub>

### 状态放进程内存

`L05-P0-004` · L5 编排与运行时层 · defect · 置信度 high

**影响**：一次发布或 OOM，跑到一半的任务全部消失。

**证据**：

- `app.py:8` — _sessions = {}

**修法**：任务状态落到外部存储（redis / pg / checkpoint），进程可重启、可迁移。

<sub>来源 L5/pits/1</sub>

### 检索没有权限过滤

`L07-P0-006` · L7 知识与检索层 · defect · 置信度 high

**影响**：A 租户的文档被 B 租户检索到，一次就够上新闻。

**证据**：

- `rag.py:2` — return vectorstore.similarity_search(query_embedding, k=5)

**修法**：检索前强制加租户/ACL 过滤，写在数据访问层，不靠每个调用点自觉。

<sub>来源 L7/pits/1</sub>

### 造一个万能工具

`L09-P0-008` · L9 工具与协议层 · defect · 置信度 high

**影响**：shell + SQL + 发邮件打包给 Agent，等于给它 root。

**证据**：

- `tools.py:1` — def run_shell(cmd: str):

**修法**：工具按动作拆细，参数白名单 + 审批 + 沙箱；不要给 Agent 一个能碰全系统的入口。

<sub>来源 L9/pits/1</sub>

### 在应用容器跑生成代码

`L10-P0-009` · L10 执行与沙箱层 · defect · 置信度 high

**影响**：共享内核，一次逃逸就是主机沦陷。

**证据**：

- `app.py:23` — return {"out": exec(payload["code"])}

**修法**：生成代码进独立沙箱（microVM / gVisor / 一次性容器），不与应用共享内核。

<sub>来源 L10/pits/1</sub>

### 把 prompt 当权限

`L14-P0-011` · L14 安全与合规层 · defect · 置信度 high

**影响**：system prompt 写「不要做 X」，实际没有任何机制拦住 X。

**证据**：

- `prompt.py:1` — SYSTEM = "你是助手。不要执行删除操作，禁止访问用户隐私数据。"

**修法**：权限写在代码里：工具白名单、参数校验、危险动作人审；prompt 只能表达意图，不能当门禁。

<sub>来源 L14/pits/1</sub>

## P1 · 应尽快修（6 条）

### 没有配额与预算上限

`L03-P1-014` · L3 身份、租户与配额层 · missing_capability · 置信度 high

**影响**：一个死循环或一次刷接口，账单当场失控。

**证据**：

- `llm_extra.py:3` — c1 = OpenAI()
- `llm_extra.py:4` — c2 = Anthropic()
- `llm_extra.py:5` — c3 = ChatOpenAI()

**修法**：每租户/每任务设 token 与调用次数上限。

<sub>来源 L3/pits/2</sub>

### 业务直连厂商 SDK

`L04-P1-003` · L4 模型接入与网关层 · risky_default · 置信度 high

**影响**：换模型要改几十处，错误码还不一样。

**证据**：

- `llm_extra.py:3` — c1 = OpenAI()
- `llm_extra.py:4` — c2 = Anthropic()
- `llm_extra.py:5` — c3 = ChatOpenAI()

**修法**：抽一层模型网关：统一鉴权、路由、fallback、重试、计量；业务只依赖网关接口。

<sub>来源 L4/pits/1</sub>

### 全量上下文硬塞

`L06-P1-005` · L6 上下文工程层 · risky_default · 置信度 high

**影响**：工具 schema 全注入、文档全塞进 prompt，模型选错还被怪「不行」。

**证据**：

- `context.py:1` — system_prompt = base_prompt + "\n".join(history)

**修法**：上下文按额度分配：system / 记忆 / 检索 / 工具 schema 各有预算，超了就压缩或拆子 Agent。

<sub>来源 L6/pits/1</sub>

### 记忆全量塞进向量库

`L08-P1-007` · L8 记忆层 · risky_default · 置信度 high

**影响**：检索回来全是噪声，还不如不记。

**证据**：

- `memory.py:2` — store.add_documents(docs)

**修法**：记忆分层：原文冷存、笔记提炼、结构化沉淀，按 TTL 淘汰，定期去重。

<sub>来源 L8/pits/1</sub>

### 没有评测就上线

`L12-P1-010` · L12 评测与优化层 · missing_capability · 置信度 medium

**影响**：「感觉还行」是唯一验收标准，换个模型后全线退化却没人知道。

**证据**：

- 未找到 ['**/evals/**', '**/eval/**', '**/golden/**', '**/badcases/**', '**/*eval*.py', '**/*.eval.ts']

**修法**：先攒 20-50 条真实任务做回归集，接进 CI；每次改 prompt/模型都跑一遍。

<sub>来源 L12/pits/1</sub>

### 成本不做归属

`L17-P1-012` · L17 成本与商业化层 · risky_default · 置信度 high

**影响**：只知道总账单，不知道哪个租户在亏钱，越用越亏。

**证据**：

- `llm_extra.py:3` — c1 = OpenAI()
- `llm_extra.py:4` — c2 = Anthropic()
- `llm_extra.py:5` — c3 = ChatOpenAI()

**修法**：每次模型调用统一埋点：tokens、模型、任务、租户，落到 usage 表，可按租户聚合与限额。

<sub>来源 L17/pits/1</sub>

## P3 · 建议（1 条）

### 没有定义「什么叫做完」

`L01-P3-013` · L1 产品与场景层 · missing_capability · 置信度 high

**影响**：没有验收定义，换模型后全线退化也没人知道。

**证据**：

- 未找到 ['README.md']
- `app.py:3` — from langchain_openai import ChatOpenAI

**修法**：写清 20-50 条真实任务与验收口径，再接模型。

<sub>来源 L1/pits/2</sub>

## 层状态

| 层 | 名称 | 状态 | 结论数 |
|---|---|---|---|
| L1 | 产品与场景层 | partial | 1 |
| L2 | 接入与交付层 | weak | 1 |
| L3 | 身份、租户与配额层 | missing | 2 |
| L4 | 模型接入与网关层 | partial | 1 |
| L5 | 编排与运行时层 | weak | 1 |
| L6 | 上下文工程层 | partial | 1 |
| L7 | 知识与检索层 | weak | 1 |
| L8 | 记忆层 | partial | 1 |
| L9 | 工具与协议层 | weak | 1 |
| L10 | 执行与沙箱层 | weak | 1 |
| L11 | 多智能体协作层 | present | 0 |
| L12 | 评测与优化层 | partial | 1 |
| L13 | 可观测与运维层 | present | 0 |
| L14 | 安全与合规层 | weak | 1 |
| L15 | 平台控制面 | present | 0 |
| L16 | 基础设施与推理层 | present | 0 |
| L17 | 成本与商业化层 | partial | 1 |

---
生成于 2026-11-27T21:58:01+08:00 · aivitals v0.1.0