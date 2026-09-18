# Eval 03：同一规则被修订版替代（superseded）

## 场景
目标公司拟申报某交易所某板块上市。交易所《某板块股票上市规则(2022修订)》第10.3条规定发行人上市前须清理对赌条款并列举四类例外情形；2025年修订版将该规则改写后移至第12.1条，例外范围收窄为两类。txn-docs 阶段做条款依据确认时，项目组仍按 2022 版引用。

## 输入

legal_authority.json 现有记录：

```json
{
  "proposition_id": "L021",
  "proposition": "发行人申报上市前应当清理对赌条款，符合列举例外情形的可以保留",
  "jurisdiction": "PRC",
  "authority_type": "exchange_rule",
  "authority_name": "某板块股票上市规则(2022修订)",
  "provision": "第10.3条",
  "issuer": "某交易所",
  "effective_status": "effective",
  "effective_date": "2022-06-01",
  "verified_at": "2026-08-28",
  "source_ref": "yuandian-law",
  "holding": "发行人应当清理申报前存续的对赌安排；符合列举的四类例外情形的可以保留",
  "limitations": "",
  "confidence": "medium"
}
```

模拟法源适配器返回：

```json
{
  "query": "某板块股票上市规则 对赌条款 清理",
  "current_version": "某板块股票上市规则(2025修订)",
  "current_status": "现行有效",
  "effective_date": "2025-07-01",
  "supersedes": "某板块股票上市规则(2022修订)",
  "matched_provision": "第12.1条",
  "matched_text": "发行人申报前应当清理全部对赌安排，仅保留本条列举的两类例外情形",
  "difference_note": "与2022版相比：条文位置由10.3移至12.1；例外情形由四类收窄为两类"
}
```

## 期望行为
1. L021 更新为 `effective_status: superseded`，limitations 注明"被 2025 修订版第12.1条取代，例外情形由四类收窄为两类"。
2. 按现行版本新开 L 编号（如 L035）：authority_name 含版本年份"某板块股票上市规则(2025修订)"，provision 为第12.1条，holding 取适配器 matched_text 逐字原文（同时发现并修正 L021 holding 中的录入噪音）。
3. txn-docs 条款依据表与报告改挂新 L 编号；**例外范围收窄的差异被显式提示**——若交易文件曾按旧四类例外出具保留意见，须标记为待复核事项，不得沿用旧口径。

## 判定标准
- ✅ 通过：L021=superseded 且取代关系完整记录；新 L 记录引用 2025 修订版第12.1条；下游引用已切换；例外收窄差异进入待复核/提示清单。
- ❌ 不通过：L021 仍为 effective 被继续引用；或新旧版本差异（四类→两类例外）未被提示，导致按旧口径出具保留意见；或新记录 authority_name 不含版本年份、无法区分新旧。

## metadata
knowledge_dimension: legal_authority
difficulty: advanced
