---
name: aivitals-fix
description: 按 AIVitals 报告的 P0 逐条修复，每轮用 baseline 复检，新增问题回退。
---

# 逐条修复

```bash
aivitals scan . --baseline .aivitals.json --update-baseline
# 改一条后
aivitals scan . --baseline .aivitals.json --out .aivitals-report
```

一次只改一条；改完必须复检；不删规则换绿灯。
