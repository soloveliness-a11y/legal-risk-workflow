# Eval 07：BP 数据与审计报告期间口径不同（BP vs audit）

## 场景
目标公司 BP（2026-07出具）写"2026年营收预计1.2亿元"；审计报告（2026-03出具，标准无保留意见，审计期间为2025会计年度）显示2025年度营收0.8亿元。初筛脚本将两个数字登记为同一命题下的冲突（C013）。两份文件各自内部均无错误。

## 输入

evidence_registry.json 冲突组 C013（初筛登记的命题 F030"目标公司营收"）：

```json
[
  {
    "evidence_id": "E044",
    "claim_id": "F030",
    "source_ref": "商业计划书_BP_v3.pdf",
    "locator": "p.12 财务概览表",
    "source_type": "BP",
    "source_date": "2026-07-15",
    "certainty": "claimed",
    "contradiction_group": "C013",
    "note": "口径：2026全年度，含下半年预测"
  },
  {
    "evidence_id": "E045",
    "claim_id": "F030",
    "source_ref": "审计报告_2025年度.pdf",
    "locator": "§2 利润表",
    "source_type": "audit",
    "source_date": "2026-03-20",
    "certainty": "confirmed",
    "contradiction_group": "C013",
    "note": "口径：2025会计年度，历史财务数据，无保留意见"
  }
]
```

## 期望行为
1. Scope consistency 前置排除伪冲突：两源命题与期间均不同（2026全年前瞻 vs 2025年度历史），不构成同一命题的实质矛盾——C013 按 `scope difference` 处理，拆分为 F030a（2025年度营收）与 F030b（2026年度营收预期）分别挂证据。
2. 分别裁决：F030a（历史数字、同期间、审计 Authority 高）以审计 0.8亿元为准；F030b（前瞻预测）BP 一律按 claimed 处理，不因审计报告存在而被"覆盖"删除，也不升级为 confirmed，如需引用须独立佐证。
3. 报告双口径分别呈现（2025实际0.8亿 ✅已确认；2026预计1.2亿 [BP声称]），不出现"审计与BP冲突、以审计为准故2026年营收应为0.8亿"式的机械覆盖结论。

## 判定标准
- ✅ 通过：C013 输出 scope difference（或等价的"非冲突、分别呈现"结论）；2025 数字以审计为准；2026 预测保持 claimed/[BP声称] 标签；命题拆分后各自可追溯证据。
- ❌ 不通过：不问期间直接"以审计为准"裁决 2026 预测不成立；或将 BP 预测与审计数字强行判为真实矛盾输出 unresolved；或合并口径后在报告中混用两数。

## metadata
knowledge_dimension: evidence_adjudication
difficulty: advanced
