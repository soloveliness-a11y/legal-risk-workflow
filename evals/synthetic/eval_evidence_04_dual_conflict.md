# Eval 08：两个独立正式来源相互矛盾（unresolved）

## 场景
尽调中就目标公司2026年3月股东会取得两份内容矛盾的正式文件：一份（公司提供）载明该次股东会"审议通过增资方案甲"，另一份（某投资机构交易留档）载明同次会议"审议通过增资方案乙"。两份文件均加盖目标公司公章、签署日期相同、无相互替代条款，签字页差异当场无法通过笔迹或用印判定，来源相互独立。

## 输入

evidence_registry.json 冲突组 C015（支撑命题 F042"2026-03股东会决议内容"）：

```json
[
  {
    "evidence_id": "E051",
    "claim_id": "F042",
    "source_ref": "股东会决议_202603_甲版本.pdf",
    "locator": "决议正文§1",
    "source_type": "signed_agreement",
    "source_date": "2026-03-18",
    "certainty": "confirmed",
    "contradiction_group": "C015",
    "note": "来源：公司提供；内容：通过增资方案甲"
  },
  {
    "evidence_id": "E052",
    "claim_id": "F042",
    "source_ref": "股东会决议_202603_乙版本.pdf",
    "locator": "决议正文§1",
    "source_type": "signed_agreement",
    "source_date": "2026-03-18",
    "certainty": "confirmed",
    "contradiction_group": "C015",
    "note": "来源：某投资机构留档；内容：通过增资方案乙；与甲版本用印位置存在细微差异"
  }
]
```

## 期望行为
1. 六维度逐项评估后无优势判断（两源 Authority/Directness/Temporal relevance 均相当，Corroboration 各为一源，无后签替代或效力优先线索）→ 输出 `unresolved`，不强行选边。
2. Dossier 对应事实保持 ⚠️不一致 **双源并列**，并升级进入 §12 关键风险信号（决议真实性/公司治理程序存疑）与 §14 待办；resolution 写明补证方向（调取登记机关备案版本、核验全体签署原件、必要时司法鉴定用印）。
3. 报告（risk-report）引用该事实时以双版本矛盾状态呈现；report-review 复核时若发现采信任一版本，应退回。

## 判定标准
- ✅ 通过：C015 的 resolution=unresolved 且写明补证方向；Dossier 双源保留并列 ⚠️；进入关键风险信号/待办；任何下游产出无单版本采信。
- ❌ 不通过：以"公司提供的版本更权威/更新"或"投资机构留档更独立"为由静默选边；或裁决为 temporally reconcilable（两文件日期相同，无时差可解释）；或 unresolved 但未登记补证方向。

## metadata
knowledge_dimension: evidence_adjudication
difficulty: basic
