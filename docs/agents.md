# 智能体 / 技能 / 工作流

AIVitals 除了命令行，还自带三类可直接被 AI 客户端加载的资产。它们不是说明书，是能被 `aivitals export` 铺进项目、能被工作流真跑起来的东西。

```bash
aivitals agent list      # 3 个智能体
aivitals skill list      # 3 个技能
aivitals workflow list   # 3 条工作流
aivitals export --to .claude   # 一次性导出到项目
```

## 三个智能体

给 Claude Code 这类支持 subagent 的客户端用（`.claude/agents/*.md`，带 `name / description / tools / model` 头）。

| 智能体 | 职责 | 工具 | 什么时候用 |
|---|---|---|---|
| `aivitals-auditor` | 体检官：跑 scan、读报告、按证据汇报 | Bash / Read / Grep / Glob | 「帮我看看这个项目架构有什么问题」 |
| `aivitals-claims` | 声明对正官：四态判定不改口径 | Bash / Read / Grep | 「README 说的这些功能真的实现了吗」 |
| `aivitals-fixer` | 修复官：一次只改一条 P0，改完复检 | Bash / Read / Edit / Grep | 「按报告把 P0 修掉」 |

三者共同写死的规矩：无 `file:line` 不写结论；未覆盖语言照实说；不评「架构优雅」；体检阶段不动代码。

## 三个技能

给支持 Skills 的客户端用（`skills/<name>/SKILL.md`，`name / description` 头）。技能比智能体更轻，只描述「怎么做」，不绑定工具集。

| 技能 | 内容 |
|---|---|
| `aivitals-audit` | 安装 → scan → 读 report.md → 四项交付 |
| `aivitals-claims` | claims → 四态口径 → 证据表 |
| `aivitals-fix` | 建基线 → 改一条 → 复检 → 回退条件 |

## 三条工作流

工作流是可执行编排，把已经验证过的 CLI 动作串起来，所以每一步都能单独复现、退出码照旧。

| 工作流 | 步骤 | 用途 |
|---|---|---|
| `audit` | scan（含 `--doc README.md`） | 本地一次体检 |
| `pr-gate` | 建基线 → `scan --fail-on P0` | CI 门禁，历史问题不阻塞新 PR |
| `fix-loop` | 建基线 → 复检 | 改完对比，只看新增与消失 |

```bash
aivitals workflow run audit --path .
aivitals workflow run pr-gate --path .     # P0 时退出码 2
aivitals workflow run fix-loop --path .    # 改完再跑，只看增量
```

### 工作流语法

```yaml
name: my-flow
description: 一句话说明
steps:
  - id: step-1
    run: scan                 # scan / claims
    with:                     # 转成命令行参数，下划线自动变连字符
      target: .               # 位置参数，不加 --
      doc: README.md
      fail_on: P0
      out: report
    continue_on_error: false  # true：非零也继续，但记录下来
```

- `with` 里的键自动映射：`update_baseline: true` → `--update-baseline`，`fail_on: P0` → `--fail-on P0`。
- `target` 是位置参数，不要写成 `--target`。
- 最后一步的退出码就是整条工作流的退出码，所以 `pr-gate` 能直接当 CI 门禁。

## 导出到项目

```bash
aivitals export                      # 默认铺到 .claude/agents、.claude/skills、.aivitals/workflows
aivitals export --to vendor/aivitals  # 想放别处
aivitals export --kind agents         # 只导智能体
```

导出的副本归你改。改包内的原件会在升级时被覆盖，建议改导出后的那一份；想长期维护就在项目里提交它们。

## 和「提示词」什么关系

- 客户端**不支持**智能体/技能/插件 → 用 `aivitals prompt` 打印一段话，粘进对话框，AI 照样能干活。
- 客户端**支持**（Claude Code / Cursor）→ 用 `aivitals export` 铺好，AI 会自己挑合适的那个。
- **CI / 定时任务** → 用 `workflow run` 或仓库根的 `action.yml`，不需要 AI 参与。

三条路径共用同一套规则与报告格式，所以结论一致。
