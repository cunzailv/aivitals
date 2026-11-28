# 提示词（直接粘给 AI）

五套模板，按场景取。都可以从命令行直接打印，避免手抄出错：

```bash
aivitals prompt --for audit            # 体检
aivitals prompt --for claims           # 声明对正
aivitals prompt --for fix              # 逐条修复
aivitals prompt --for ci               # CI 接入
aivitals prompt --for audit --lang en  # 英文
aivitals prompt --for audit --copy     # 顺带复制到剪贴板（macOS）
```

共同约束（每套都写了）：结论必须带 `file:line`、先给方案不动代码、不评「架构优雅」。

---

## 1. 体检（默认）

```text
你是我的 AI 项目架构体检助手。请用 AIVitals 检查当前仓库，结论必须来自报告，不要凭印象点评。

第 1 步：确认可用
    aivitals --version
若没有，安装（国内网络用第二条）：
    pip install "https://github.com/cunzailv/aivitals/raw/main/releases/aivitals-0.2.1-py3-none-any.whl"
    pip install "https://gh-proxy.com/https://github.com/cunzailv/aivitals/raw/main/releases/aivitals-0.2.1-py3-none-any.whl"

第 2 步：扫描，并把 README 的宣称一起对正
    aivitals scan . --doc README.md --format md,json --out .aivitals-report

第 3 步：读 .aivitals-report/report.md，按这个格式回答：
【结论】总体档位、P0/P1 数量、最该先修的一条
【P0 清单】每条：`文件:行号` · 问题 · 为什么在这档位会出事 · 最小改法
【覆盖与局限】原样说明未覆盖的语言/层
【下一步】按依赖顺序 1-3 个动作

约束：
- 没有 file:line 证据的结论不要写
- 不要自动改代码，先给方案
- 不评「架构优雅」「技术选型好坏」
- 配了 MCP（aivitals mcp）时优先调 audit_repo 工具
```

> 上面是 0.2.1 的真实链接；升级版本后跑 `aivitals prompt --for audit` 取当前版本的准确 URL。

---

## 2. 声明对正

```text
用 AIVitals 校验这个项目的 README 宣称与代码是否对得上，不要靠读代码猜。

    aivitals claims . --doc README.md --out .aivitals-claims

读 .aivitals-claims/claims.md，逐条按四态汇报：
- confirmed：代码里有实现证据
- partial：有实现但缺关键约束（例如 tenant_id 被硬编码）
- contradicted：代码与宣称矛盾 —— 必须给出 `文件:行号`
- unsupported：没找到证据 —— 只能写「未找到证据」，不能写成「没实现」

最后给一张表：宣称 / 判定 / 证据 / 建议补什么。不做法律或合规定性。
```

---

## 3. 逐条修复

```text
按 .aivitals-report/report.md 里的 P0 逐条修，一次只处理一条。

1) 先建基线：aivitals scan . --baseline .aivitals.json --update-baseline
2) 修一条 → aivitals scan . --baseline .aivitals.json --out .aivitals-report
3) 确认该条消失，且没有新增 P0/P1；有新增就回退
4) 通过后再做下一条

每轮告诉我：改了哪些文件、哪条消失了、有没有新增问题。不要一次改五处。
```

---

## 4. 接 CI

```text
给这个仓库接上 AIVitals 门禁，让 PR 能自动拦 P0。

1) 先建基线（否则历史问题会让 CI 一直红）：
   aivitals scan . --baseline .aivitals.json --update-baseline
2) 新建 .github/workflows/aivitals.yml：
   - uses: cunzailv/aivitals@main
   - with: path=. / fail-on=P0 / out=aivitals-report
   - 上传 SARIF 到 GitHub Code Scanning
3) 本地验证：aivitals scan . --fail-on P0，确认退出码（P0 时是 2）
4) 告诉我在 GitHub 上还需要开什么权限
```

---

## 5. Audit (English)

```text
You are my AI-project architecture auditor. Use AIVitals — every conclusion must come from its report.

1) `aivitals --version`; if missing: pip install "https://github.com/cunzailv/aivitals/raw/main/releases/aivitals-0.2.1-py3-none-any.whl"
2) `aivitals scan . --doc README.md --format md,json --out .aivitals-report`
3) Read `.aivitals-report/report.md`, answer with:
   - Verdict: overall, P0/P1 counts, most urgent fix
   - P0 list: `file:line` · what's wrong · why it breaks at this maturity · minimal fix
   - Coverage: uncovered languages/layers exactly as reported
   - Next: 1-3 actions in dependency order
Rules: no claim without file:line; do not edit code before I confirm; no "elegance" judgments.
```

---

## 为什么这样写

- **把安装写进提示词**：用户粘给 AI 时，AI 多半没装过，不写就会退回「我只能给你建议」。
- **规定输出格式**：不给格式，AI 会写一大段散文；给了四项，它只能照填。
- **写死四态口径**：否则 AI 容易把「没找到证据」说成「你根本没实现」。
- **禁止直接改代码**：体检和修复是两件事，混在一起会一次改十个文件，没人敢合。
