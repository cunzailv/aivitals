---
name: aivitals-claims
description: 用 AIVitals 校验文档宣称与代码实现是否一致，输出 confirmed/partial/contradicted/unsupported 四态与证据。
---

# 声明对正

```bash
aivitals claims <path> --doc README.md --out .aivitals-claims
```

四态口径见 `docs/architecture.md`。`unsupported` 只能写「未找到证据」。
