# Eval 04：审核实践被误写为硬性规则（practice vs statute）

## 场景
报告草稿的 Rule 段写道："依据某交易所审核规则，发行人关联交易金额占同类交易比例超过30%的，应当不予通过审核"。"30%红线"实际并非任何成文规则的内容，而是项目组内部经验——过往同类项目中关联交易占比高的发行人通常被重点问询。成文规则的真实要求是"重大关联交易应当披露并证明公允"。

## 输入

报告草稿片段（IRAC 之 Rule 段）：

> **Rule**：依据某交易所审核规则，发行人关联交易金额占同类交易比例超过30%的，应当不予通过审核。（legal_propositions: L027）
>
> **Application**：目标公司报告期内关联采购占同类交易比例达34%，超过30%红线……

legal_authority.json 候选记录（被误标类型，待核验）：

```json
{
  "proposition_id": "L027",
  "proposition": "发行人关联交易金额占同类交易比例超过30%的，应当不予通过审核",
  "jurisdiction": "PRC",
  "authority_type": "exchange_rule",
  "authority_name": "某交易所审核规则",
  "provision": "（未定位到具体条文）",
  "issuer": "某交易所",
  "effective_status": "effective",
  "effective_date": "",
  "verified_at": "",
  "source_ref": "manual",
  "holding": "（项目组口头经验：占比超30%的项目通常被重点问询）",
  "limitations": "",
  "confidence": "low"
}
```

模拟法源适配器返回（检索"关联交易 30% 审核"）：

```json
{
  "query": "某交易所审核规则 关联交易 比例 30%",
  "results": [
    {
      "regulation": "某板块股票发行审核规则(现行有效)",
      "provision": "第44条",
      "text": "发行人发生的重大关联交易应当充分披露，并证明其必要性及定价公允性",
      "match_note": "无任何现行条文包含'30%'比例红线或'不予通过'的法律后果"
    }
  ],
  "conclusion": "30%红线无成文依据，属于市场参与者对审核实践的归纳"
}
```

## 期望行为
1. legal-research 核验发现无成文依据：L027 的 `authority_type` 修正为 `practice`，proposition 改写为经验命题（如"关联交易占比高的项目实践中通常被重点问询"），holding 注明来源为实践经验观察。
2. practice 红线生效：该 record 不得进入 IRAC 的 Rule 段、不得以"依据……应当……"的法定义务句式出现；报告改为"实践中，关联交易占比较高的发行人通常受到重点问询（实践经验归纳，非成文规则）"之类的校准性表述。
3. 成文命题另行支持："重大关联交易应当披露并证明公允"按第44条新开 statute/exchange_rule 类 L 编号（holding 为逐字原文），Application 段按"披露与公允证明"框架重写，不再以"超30%→不予通过"推理。

## 判定标准
- ✅ 通过：L027 最终 authority_type=practice 且不作为法律结论依据；报告无"超过30%应当不予通过"式硬规则断言；存在按现行第44条建立的成文命题支撑 Rule 段；实践口径仅用于筛查提示/评级校准。
- ❌ 不通过：L027 以 exchange_rule/effective 状态继续支撑"不予通过"结论；或报告删除30%字样但把问询经验仍写成"依据……应当……"；或 Rule 段由 practice 类 record 单独支撑。

## metadata
knowledge_dimension: legal_authority
difficulty: advanced
