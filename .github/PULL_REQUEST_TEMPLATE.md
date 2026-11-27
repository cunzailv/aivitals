## 改了什么

<!-- 一句话 -->

## 类型

- [ ] 新规则（`aivitals/data/checks/L*.yaml`）
- [ ] 规则修正（误报 / 漏报）
- [ ] 引擎
- [ ] 文档 / 其他

## 验证

```
aivitals eval --verbose
python -m pytest -q
```

粘贴关键输出：

## 规则自查（新增规则必填）

- [ ] 有 `derived_from`，能指回 17 层体系的具体字段
- [ ] 有 `impact` 与 `fix`
- [ ] 在至少一个 fixture 上验证命中，或新增最小 fixture
- [ ] 没有引入语义猜测（只匹配结构性写法）
