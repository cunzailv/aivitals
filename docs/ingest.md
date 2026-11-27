# 喂资料：把文档变成候选规则

体检的准确度来自规则库，规则库来自对架构问题的持续积累。`aivitals ingest` 负责第一步：把一份文档切成节，抽出「像规则」的句子，标好层与级别，放进待审目录。

它不是自动生成规则。**候选不参与扫描**，必须人工补上检测条件与样例才会生效——否则规则库会变成一堆无法验证的噪音。

## 用法

```bash
aivitals ingest --source ./报告.md --id geo-2026
aivitals ingest --source ./report.docx --id geo-2026
aivitals ingest --source ./page.html --id arch-notes --no-source
```

支持 md / txt / html / docx / pdf：

- `docx` 需要 `pip install python-docx`，会保留 Heading 层级与表格内容
- `pdf` 需要 `pip install pypdf`，抽取质量取决于源文件是否有文本层

## 产出

```
corpus/sources/<id>/            # 原文，私有，已被 .gitignore 排除
  canonical.md
  sections.json                 # 章节树
  manifest.json                 # sha256 / 字数 / 是否可发布
aivitals/data/checks/_draft/<id>.candidates.yaml   # 候选，同样不进公开仓库
```

候选结构：

```yaml
- id: CAND-8f3a1c2d
  layer_hint: 7          # 关键词推断，可能不准，需人核
  severity_hint: P0      # 「必须/禁止」→P0，「建议」→P2，其余 P1
  section: 检索与知识层
  text: 检索必须按租户过滤，否则会越权拿到别人的文档
  detect: 待人工转写：拆成 globs + pattern + 必须缺失的反证
```

## 晋升流程

1. 打开 `_draft/<id>.candidates.yaml`，按 `layer_hint` 分组浏览。
2. 挑真正可静态验证的句子——能说清「代码里出现什么就是错」的才留。
3. 转写 `detect`：`globs`（限定语言与目录）+ `pattern` + 用 `none` 写反证（已有缓解措施就不报）。
4. 把它移进 `aivitals/data/checks/L{层}.yaml`，补 `impact`、`fix`、`derived_from`。
5. 加一个最小 fixture（`fixtures/<name>/` + `expected.json`），跑：

```bash
aivitals eval --verbose
```

召回不升、或误报增加，就退回候选池。

## 经验阈值

- 一份 1 万字报告通常出 20–40 条候选，最终能转成稳定规则的是 3–8 条。
- 含「必须 / 禁止 / 否则 / 会导致」的句子命中率最高；纯描述性段落基本抽不出东西。
- 层判错很常见（一句话同时提到检索和租户），以人工判断为准，`layer_hint` 只是排序建议。

## 隐私

- 原文只落 `corpus/sources/`，该目录在 `.gitignore` 里，不会进公开仓库。
- 候选里只保留句子本身与章节名，不含原文大段引用；如果你连句子都不想公开，加 `--no-source` 并自行清理 `_draft`。
- `_draft/` 也已加入 `.gitignore`。
