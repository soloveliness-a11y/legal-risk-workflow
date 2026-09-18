# Eval 12：R→L→authority chain 完整性校验

## 场景
report-review 阶段对定稿前产物做 authority audit。risk_matrix.json 中 R12 挂了两个法源命题引用 `["L034", "L041"]`；legal_authority.json 中 L041 存在但 `effective_status: amended`，L034 完全不存在（孤儿引用），另有一个正常记录 L036（effective）作为对照项，用于检验审计不误伤。

## 输入

risk_matrix.json 片段：

```json
[
  {
    "risk_id": "R12",
    "risk_title": "目标公司股东出资期限约定不合规",
    "severity": "中🟡",
    "legal_propositions": ["L034", "L041"],
    "clause_mapping_hints": { "target_file": "增资协议", "clauses": ["§3.1 出资期限"] }
  },
  {
    "risk_id": "R13",
    "risk_title": "关联交易未履行内部决议程序",
    "severity": "中🟡",
    "legal_propositions": ["L036"],
    "clause_mapping_hints": {}
  }
]
```

legal_authority.json 片段：

```json
{
  "records": [
    {
      "proposition_id": "L036",
      "proposition": "关联交易应当履行公司内部决议程序",
      "authority_type": "statute",
      "authority_name": "某公司治理条例(现行)",
      "provision": "第15条",
      "effective_status": "effective",
      "verified_at": "2026-09-01",
      "confidence": "high"
    },
    {
      "proposition_id": "L041",
      "proposition": "股东认缴出资期限不得超过法定上限",
      "authority_type": "statute",
      "authority_name": "某市场主体出资管理规定(2019版)",
      "provision": "第7条",
      "effective_status": "amended",
      "verified_at": "2026-09-01",
      "limitations": "2025年修订后条号已变，须改引现行版本",
      "confidence": "medium"
    }
  ]
}
```

## 期望行为
1. chain 校验逐条执行并**两项问题全部检出**：R12→L034 为孤儿引用（legal_authority.json 中不存在）；R12→L041 引用的 record 非 effective（amended）。对照项 R13→L036 校验通过，不受牵连。
2. 校验结果显式输出 FAIL/退回（不静默放行），并给出修复路径：L034 补建 record（完成核验）或从 risk_matrix 移除该引用；L041 在报告正文显式标注"已修订"，并按现行版本新开 L 编号后改挂。
3. 修复后复验通过的条件：risk_matrix 中每个 legal_propositions 引用均能在 legal_authority.json 中找到且 effective_status=effective（非 effective 引用必须在正文显式标注），无重复 proposition_id。

## 判定标准
- ✅ 通过：L034 孤儿引用与 L041 非 effective 两项均被检出并逐项报告；审计结论为不通过/退回；L036 未被误报；修复路径明确且修复后可复验。
- ❌ 不通过：任一问题漏检（尤其只报孤儿引用、放过 amended 引用，或反之）；审计静默通过；L036 被误判为问题项；或校验只比对编号存在性、不检查 effective_status。

## metadata
knowledge_dimension: system_behavior
difficulty: advanced
