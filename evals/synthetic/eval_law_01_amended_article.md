# Eval 01：法条编号因修法漂移（amended）

## 场景
目标公司（某科技公司）历史沿革章节撰写中，报告草稿引用《某市场主体登记管理若干规定(2019版)》第18条，支持"股权转让后公司应当办理股东变更登记"这一命题。该规定已于2025年修订：原第18条内容经调整后移至第21条，义务表述有实质变化（新增线上办理时限要求）。法条编号与内容均发生漂移。

## 输入

报告草稿片段：

> 依据《某市场主体登记管理若干规定》第18条，目标公司本次股权转让后应当及时办理股东变更登记。（legal_propositions: L012）

legal_authority.json 现有记录（按旧版填写，待核验）：

```json
{
  "proposition_id": "L012",
  "proposition": "股权转让后公司应当办理股东变更登记",
  "jurisdiction": "PRC",
  "authority_type": "regulation",
  "authority_name": "某市场主体登记管理若干规定(2019版)",
  "provision": "第18条",
  "issuer": "某省级市场监督管理部门",
  "effective_status": "effective",
  "effective_date": "2019-05-01",
  "verified_at": "2026-09-10",
  "source_ref": "qcc-legal-regulation",
  "holding": "公司股权转让后应当向登记机关申请变更登记",
  "limitations": "",
  "confidence": "medium"
}
```

模拟法源适配器返回（legal-research 检索现行版本时得到）：

```json
{
  "query": "某市场主体登记管理若干规定 股权变更登记",
  "current_version": "某市场主体登记管理若干规定(2025修订)",
  "current_status": "现行有效",
  "effective_date": "2025-10-01",
  "matched_provision": "第21条",
  "matched_text": "股东转让股权的，公司应当自股权转让之日起三十日内通过登记平台申请变更登记",
  "note": "原第18条经2025年修订调整后移至第21条，并新增三十日办理时限"
}
```

## 期望行为
1. legal-research 检出条号漂移：L012 更新为 `effective_status: amended`，limitations 注明"2025年修订后原第18条内容移至第21条"，verified_at 刷新。
2. 按现行版本**新开 L 编号**（如 L031）引用第21条，holding 采用适配器返回的逐字原文；L012 保留旧编号并维护新旧映射，不得原地改写 L012 的 provision 字段冒充"一直正确"。
3. 报告引用更新为现行版本（含三十日时限的新义务内容），或显式标注"原第18条已修订，现行第21条"；不出现把旧条号当现行依据的表述。

## 判定标准
- ✅ 通过：L012 标记 amended 且保留旧条号信息；存在新 L 记录引用 2025 修订版第21条（holding 为逐字原文）；报告正文不再以第18条作为现行依据；新旧编号映射关系可查。
- ❌ 不通过：L012 原地把"第18条"改成"第21条"且状态仍 effective；或报告继续引用旧条号且无修订标注；或新记录的 holding 凭记忆默写而非适配器逐字原文。

## metadata
knowledge_dimension: legal_authority
difficulty: advanced
