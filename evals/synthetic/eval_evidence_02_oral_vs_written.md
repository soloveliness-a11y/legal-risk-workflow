# Eval 06：访谈陈述与签署合同冲突（oral vs written）

## 场景
dd-interview 中创始人A陈述："与某供应商签订的三年期独家供货协议已于上月协商一致解除，不再执行"。档案中的书面协议（2026-06-01生效，有效期三年，含独家供货义务）之后未见任何解除协议、终止函或书面变更文件。初筛将访谈陈述与书面协议登记为冲突。

## 输入

evidence_registry.json 冲突组 C011（支撑命题 F021"独家供货义务存续状态"）：

```json
[
  {
    "evidence_id": "E031",
    "claim_id": "F021",
    "source_ref": "访谈纪要_20260905.md",
    "locator": "模块A §3 供应商合作",
    "source_type": "interview",
    "source_date": "2026-09-05",
    "certainty": "claimed",
    "contradiction_group": "C011",
    "note": "陈述人：创始人A；陈述：独家协议已口头解除，正在走流程"
  },
  {
    "evidence_id": "E032",
    "claim_id": "F021",
    "source_ref": "独家供货协议.pdf",
    "locator": "§1.2 独家义务、§9 期限（2026-06-01至2029-05-31）、§12 变更须书面",
    "source_type": "signed_agreement",
    "source_date": "2026-06-01",
    "certainty": "confirmed",
    "contradiction_group": "C011"
  }
]
```

## 期望行为
1. 按六维度裁决：书面协议在 Directness（直接约定该事项）与 Legal operativeness（已生效、变更须书面）上高于访谈陈述；协议本身约定"变更须书面"，口头解除不满足协议约定的形式要件。
2. 反向检查完成且留痕：检索全部交易文件中是否存在签署在后的补充协议、解除协议或书面变更函——本案未发现；同时评估创始人A对该事项的处分权限（其为协议签署主体，权限本身不构成瑕疵）。
3. 结论：协议版本作为当前事实依据（独家义务存续），访谈陈述不覆盖书面协议，按 📌待核实 处理并保留为线索；resolution 写明补证方向——取得双方签署的书面解除文件或供应商确认函；解除主张在报告（如适用）中只能以"公司称已解除（待核）"呈现。

## 判定标准
- ✅ 通过：裁决依据指向 Directness/Legal operativeness 维度（非"来源独立与否"）；协议义务存续作为工作口径；访谈未升级为 confirmed、未覆盖协议；补证方向明确登记；报告呈现含"待核"限定。
- ❌ 不通过：以访谈"更新、更直接来自知情人的陈述"为由认定协议已解除；或未做反向文件检查即裁决；或裁决后访谈记录被删除而非保留为线索。

## metadata
knowledge_dimension: evidence_adjudication
difficulty: advanced
