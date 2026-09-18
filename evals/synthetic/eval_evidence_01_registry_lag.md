# Eval 05：工商登记滞后于已交割协议（registry lag）

## 场景
目标公司股权结构核查发现不一致：工商登记信息显示创始人A持股60%，而公司提供的股权转让协议（2026-08-20签署）及银行付款凭证、交割确认函显示创始人A已向某投资机构转让25%股权并完成交割，交割后创始人A持股35%。工商变更登记尚未办理。初筛把两源登记为冲突。

## 输入

evidence_registry.json 冲突组 C007（支撑命题 F015"创始人A当前持股比例"）：

```json
[
  {
    "evidence_id": "E012",
    "claim_id": "F015",
    "source_ref": "qcc_cache.json / 公示系统查询快照",
    "locator": "shareholders.actual_controller",
    "source_type": "registry",
    "source_date": "2026-09-10",
    "certainty": "confirmed",
    "contradiction_group": "C007"
  },
  {
    "evidence_id": "E013",
    "claim_id": "F015",
    "source_ref": "股权转让协议.pdf + 付款凭证.pdf + 交割确认函.pdf",
    "locator": "协议§2.1、§6.3；确认函全文",
    "source_type": "signed_agreement",
    "source_date": "2026-08-20",
    "certainty": "confirmed",
    "contradiction_group": "C007"
  }
]
```

Dossier §2 草稿（待裁决回写）：

> 创始人A持股比例：60%（来源：工商登记，2026-09-10）⚠️不一致 —— 另见股转协议显示交割后35%。

## 期望行为
1. 按裁决框架"工商登记 vs 后签股转协议"场景依次确认：协议已签署生效（生效条件成就）→ 对价已支付、交割确认函已出具 → 工商变更尚在办理期。结论输出 `temporally reconcilable`，并写明时差原因（登记更新滞后，非真实股权差异）。
2. Dossier 按协议交割后口径认定创始人A持股35%，**两源记录均保留**（E012/E013 不删除），标注"工商登记待更新"并将工商变更办理列入 §14 待办。
3. 不输出"以工商登记/QCC数据为准"的静默覆盖，也不将 60% 与 35% 判为真实冲突上调风险等级（除非发现法定办理期限已逾期）。

## 判定标准
- ✅ 通过：C007 的 resolution 为 temporally reconcilable 且注明时差原因；Dossier 采用交割后口径35%并保留双源；工商变更进入待办清单；无"以登记为准"式选边。
- ❌ 不通过：以 registry 来源"更权威/独立"为由认定 60% 为准；或将两源判为真实矛盾输出 unresolved；或裁决后 Dossier 只剩单一来源记录。

## metadata
knowledge_dimension: evidence_adjudication
difficulty: basic
