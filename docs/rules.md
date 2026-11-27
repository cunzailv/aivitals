# 规则编写指南

一条规则只有同时满足三件事才允许合并：

1. **能被证据验证**：结论必须指向 `file:line`、配置键、依赖或声明原文。
2. **能区分档位**：`prototype` 阶段不应因为「没有多租户」被判红。
3. **能被回归**：改这条规则不会让健康仓库出现误报。

## 文件结构

按层分文件：`checks/L02.yaml`、`checks/L14.yaml`……

```yaml
yaml_version: 0.1
as_of: 2026-11-27
checks:
  - id: L02-P0-001
    layer: 2
    group: A
    title: 同步接口里跑长任务
    severity: P0            # P0 | P1 | P2 | P3
    kind: defect            # defect | risky_default | tradeoff | missing_capability
    derived_from: L2/pits/1
    applies_to: [ai_native_app, ai_enabled_app]
    maturity_gate: prototype
    detect:
      all_of: [...]
    impact: 网关先超时，后台还在烧 token。
    fix: 入队 → 返回 task_id → 前端订阅进度。
```

## 字段约束

| 字段 | 要求 |
|---|---|
| `id` | `L{层}-{级别}-{序号}`，全局唯一 |
| `severity` | P0 只会是「漏钱/漏数据/串租户/上线即事故」 |
| `kind` | `defect` 确定缺陷；`risky_default` 危险默认；`tradeoff` 设计取舍；`missing_capability` 能力缺失 |
| `maturity_gate` | 从哪个档位开始报。prototype < internal < production < multi_tenant |
| `derived_from` | 必须指回 17 层体系里的条目 |
| `as_of` | 规则依据的日期，过期要复审 |

## 检测原语

| 类型 | 语义 | 证据 |
|---|---|---|
| `regex_any` | 任意文件任意行命中即真 | `file:line` |
| `regex_count` | 命中数 ≥ `min` 才为真 | `file:line` |
| `none` | **没有任何**命中才为真（用于「缺少缓解措施」） | 无 |
| `file_exists` | glob 有匹配 | 文件列表 |
| `file_absent` | glob 无匹配（用于「没有评测目录」） | 缺失声明 |
| `dep_any` / `dep_none` | 依赖清单里出现/未出现 | 依赖清单 |

组合：`all_of`（全部真）、`any_of`（任一真）。出现「不适用」信号时整条规则跳过，并写进报告的「未执行检查」。

## 三条硬规矩

1. **`none` 只能用来表达「缺少缓解」，不能用来猜「没做」。** 「没搜到 `redis` 字样」不等于「没用外部存储」，所以这类规则最好同时给 `confidence: medium`。
2. **不要把泛词写进 pattern。** 第一版用 `采样` 匹配声明，单篇文档命中 82 次，全是假阳性。用短语（`支持至少两类引擎`）或带上下文（`tenant_id` + `filter=`）。
3. **一条规则只回答一个问题。** 「既查无幂等又查无审计」会让证据指向混乱，拆成两条。

## 新增规则的最小流程

1. 在 `checks/L{层}.yaml` 加条目，写 `derived_from`
2. 在 `fixtures/` 造一个能触发它的最小样例，并写进 `expected.json`
3. 跑 `aivitals eval --verbose`，确认 `recall` 上升且**误报仍为 0**
4. 报告里验证证据真的指到了对的代码行
