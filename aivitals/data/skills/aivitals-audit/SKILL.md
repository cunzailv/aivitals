---
name: aivitals-audit
description: 用 AIVitals 给 AI 项目做架构体检：17 层缺层、易出 bug 的架构模式、README 宣称对正，输出带 file:line 证据的分级报告。用户要求体检、找架构隐患、评估 AI 项目成熟度时使用。
---

# AIVitals 架构体检

## 前置

```bash
aivitals --version || pip install "https://github.com/cunzailv/aivitals/raw/main/releases/aivitals-0.3.0-py3-none-any.whl"
```

## 执行

```bash
aivitals scan <path> --doc README.md --format md,json,sarif --out .aivitals-report
```

## 读取

只读 `.aivitals-report/report.md`。要点：

- 结论行给出总体档位、P0/P1 数量
- 每条问题带 `文件:行号`
- 「覆盖与局限」段说明未覆盖语言/层

## 交付

四项：结论 / P0 清单（file:line·问题·后果·最小改法）/ 覆盖与局限 / 下一步。

## 禁止

- 无证据结论
- 假装扫过未覆盖语言
- 直接改代码
