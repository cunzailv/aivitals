"""给 AI 的提示词模板。

用户复制粘贴给任意 AI 助手（Claude / Cursor / ChatGPT / 豆包），
让 AI 用 AIVitals 去检查项目，而不是凭印象点评。
"""
from __future__ import annotations

INSTALL_URL = "https://github.com/cunzailv/aivitals/raw/main/releases/aivitals-{version}-py3-none-any.whl"
PROXY_URL = "https://gh-proxy.com/https://github.com/cunzailv/aivitals/raw/main/releases/aivitals-{version}-py3-none-any.whl"

AUDIT_ZH = """你是我的 AI 项目架构体检助手。请用 AIVitals 检查当前仓库，结论必须来自报告，不要凭印象点评。

第 1 步：确认可用
    aivitals --version
若没有，安装（国内网络用第二条）：
    pip install "{url}"
    pip install "{proxy}"

第 2 步：扫描，并把 README 的宣称一起对正
    aivitals scan . --doc README.md --format md,json --out .aivitals-report

第 3 步：读 .aivitals-report/report.md，按这个格式回答：

【结论】三行：
- 总体（critical_gaps / weak / adequate / insufficient_coverage / unsupported_language）
- P0 几条、P1 几条
- 最该先修的一条是什么

【P0 清单】每条一行：
- `文件:行号` · 问题是什么 · 为什么在这档位会出事 · 最小改法
只写报告里有的证据，不要补报告没提到的。

【覆盖与局限】原样说明报告里哪些语言/层没覆盖；不要假装扫过。

【下一步】按依赖顺序给 1-3 个动作，说明先做哪个、为什么。

约束：
- 没有 file:line 证据的结论不要写
- 不要自动改代码，先给方案，等我确认
- 不评「架构优雅」「技术选型好坏」这类主观项
- 若本机配了 MCP（aivitals mcp），优先调用 audit_repo 工具，而不是命令行"""

AUDIT_EN = """You are my AI-project architecture auditor. Use AIVitals — every conclusion must come from its report, no impressions.

1) Check: `aivitals --version`. If missing: pip install "{url}"
2) Run: `aivitals scan . --doc README.md --format md,json --out .aivitals-report`
3) Read `.aivitals-report/report.md`, then answer as:
   - Verdict: overall status, P0/P1 counts, the single most urgent fix
   - P0 list: `file:line` · what's wrong · why it breaks at this maturity · minimal fix
   - Coverage: state uncovered languages/layers exactly as reported; never pretend they were scanned
   - Next: 1-3 actions in dependency order
Rules: no claim without file:line evidence; do not edit code before I confirm; no subjective "elegance" judgments. Prefer the `audit_repo` MCP tool when available."""

CLAIMS_ZH = """用 AIVitals 校验这个项目的 README 宣称与代码是否对得上，不要靠读代码猜。

    aivitals claims . --doc README.md --out .aivitals-claims

读 .aivitals-claims/claims.md，逐条汇报，四态含义：
- confirmed：代码里有实现证据
- partial：有实现但缺关键约束（例如 tenant_id 被硬编码）
- contradicted：代码与宣称矛盾 —— 必须给出 `文件:行号`
- unsupported：没找到证据 —— 只能写「未找到证据」，不能写成「没实现」

最后给我一张表：宣称 / 判定 / 证据 / 建议补什么。不要做法律或合规定性。"""

FIX_ZH = """按 .aivitals-report/report.md 里的 P0 逐条修，一次只处理一条。

流程：
1) 先建基线，避免历史问题干扰判断：`aivitals scan . --baseline .aivitals.json --update-baseline`
2) 修一条 → `aivitals scan . --baseline .aivitals.json --out .aivitals-report`
3) 确认该条消失，且没有新增 P0/P1；有新增就回退这次改动
4) 一条通过后再做下一条

每轮告诉我：改了哪些文件、哪条消失了、有没有新增问题。不要一次改五处。"""

CI_ZH = """给这个仓库接上 AIVitals 门禁，让 PR 能自动拦 P0。

1) 先建基线（否则历史问题会让 CI 一直红）：
   aivitals scan . --baseline .aivitals.json --update-baseline
2) 新建 .github/workflows/aivitals.yml：
   - uses: cunzailv/aivitals@main
   - with: path=. / fail-on=P0 / out=aivitals-report
   - 上传 SARIF 到 GitHub Code Scanning
3) 本地先验证一遍：`aivitals scan . --fail-on P0`，确认退出码符合预期（P0 时是 2）
4) 告诉我在 GitHub 上还需要点什么（开启 Code Scanning 权限等）"""

TEMPLATES = {
    ("audit", "zh"): AUDIT_ZH,
    ("audit", "en"): AUDIT_EN,
    ("claims", "zh"): CLAIMS_ZH,
    ("fix", "zh"): FIX_ZH,
    ("ci", "zh"): CI_ZH,
}


def render(kind: str = "audit", lang: str = "zh", version: str = "0.2.1") -> str:
    key = (kind, lang)
    if key not in TEMPLATES:
        # 缺失语种时回落到中文同场景
        key = (kind, "zh")
    if key not in TEMPLATES:
        raise KeyError(f"未知提示词场景：{kind}（可选 audit / claims / fix / ci）")
    return TEMPLATES[key].format(
        url=INSTALL_URL.format(version=version),
        proxy=PROXY_URL.format(version=version),
    )
