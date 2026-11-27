# Contributing

最短路径：改规则 → 跑 `aivitals eval` → 跑测试 → 提 PR。

## 本地开发

```bash
git clone git@github.com:cunzailv/aivitals.git
cd aivitals
python3 -m venv .venv && source .venv/bin/activate
pip install -e . pytest
python -m pytest -q
aivitals eval
```

## 加一条规则

1. 在 `aivitals/data/architecture.json` 里找到对应的层，确认这条规则能指回 `comps` / `decisions` / `pits` / `check` 之一。
2. 在 `aivitals/data/checks/L{层号}.yaml` 里追加，字段说明见 `docs/rules.md`。
3. 必须填 `derived_from`（如 `L7/pits/2`）、`impact`、`fix`，否则评审直接拒。
4. 至少在一个 fixture 上验证命中，或新增一个最小 fixture（含 `expected.json`）。
5. `aivitals eval` 必须仍是 `recall ≥ 0.8` 且 `false_positive = 0`。

### 三条硬规矩

- **无证据不输出**：规则命中但取不到 `file:line`，只能记 `skipped`，不能报。
- **不做语义猜测**：正则只能匹配结构性写法，不能凭变量名推断意图。
- **不制造新层级**：规则必须挂在已有 17 层上；要加层先改 `architecture.json` 并说明理由。

## 加一条谓词（声明对正）

在 `aivitals/data/claims/predicates.yaml` 追加，必须有：

- `id`、`claim_patterns`（中英都要有）
- `scope`（core 或领域包名）
- `acceptance_ref`（指回验收清单章节）
- `signals`（证明「已实现」的代码特征）与 `anti_signals`（证明「没实现/假实现」的特征）

改完跑：

```bash
aivitals claims fixtures/claims-demo --out /tmp/c
```

四态都要有样例覆盖，否则加 fixture。

## 改引擎

- 任何会改变判定结果的改动，必须同时更新或新增 fixture，并在 PR 里贴 `aivitals eval` 输出。
- 报告字段是对外契约：`report.json` 的字段改名要同步改 README 与 `docs/architecture.md`。
- 新增原语要在 `docs/rules.md` 的原语表里登记，并补单测。

## 提交信息

```
feat(L7): 检索结果未做权限过滤
fix(detect): 正则大小写敏感导致漏判
docs(mcp): 补 Cursor 配置
```

## 许可

代码 Apache-2.0；规则与体系数据 CC-BY-4.0（见 `LICENSE-CORPUS`）。提交即表示同意以对应许可发布。
