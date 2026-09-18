# Eval 10：仅有公司单方陈述的事实（single-source claim）

## 场景
目标公司 BP（2026-08出具）与尽调访谈（财务负责人B，2026-09-05）均声称"5项核心专利权属清晰、无纠纷、无对外许可负担"。项目组尚未取得专利登记簿副本，也未做任何独立检索。两处陈述内容一致，但均出自公司单方。

## 输入

evidence_registry.json（支撑命题 F068"核心专利无权属纠纷及许可负担"）：

```json
[
  {
    "evidence_id": "E072",
    "claim_id": "F068",
    "source_ref": "商业计划书_BP_v2.pdf",
    "locator": "p.5 知识产权",
    "source_type": "BP",
    "source_date": "2026-08-10",
    "certainty": "claimed"
  },
  {
    "evidence_id": "E073",
    "claim_id": "F068",
    "source_ref": "访谈纪要_20260905.md",
    "locator": "模块A §2 IP",
    "source_type": "interview",
    "source_date": "2026-09-05",
    "certainty": "claimed"
  }
]
```

Dossier §5 草稿：

> 核心专利（5项）：权属清晰，无纠纷、无许可负担（来源：BP及访谈）。

## 期望行为
1. BP 与访谈同为公司自述，来源不相互独立（Corroboration 不因陈述重复而提升）：E072/E073 均保持 claimed，Dossier 事实保持 `[BP声称]` 标签（或等价的"公司单方陈述"标注），不升级为 ✅已确认。
2. 标签传导不丢失、不升级：下游（risk-report、risk_matrix、条款落实表）引用该事实时标签保留；报告表述为"据公司陈述，核心专利权属清晰（待登记簿副本核验）"。
3. 登记补证方向并进 pending：调取专利登记簿副本/办理专利检索、核查质押与许可登记；在补证完成前，涉及 IP 的风险定级不得以"权属清晰"为已确认前提。

## 判定标准
- ✅ 通过：F068 保持 claimed/[BP声称]，无 ✅已确认 升级；两源未被视为"独立来源相互印证"；下游引用处标签可见；补证项进入待办清单。
- ❌ 不通过：以"BP与访谈相互印证，两源一致"为由升级 confirmed；或 Dossier/报告直接写"权属清晰"无来源限定；或标签在传导到 risk_matrix 时丢失。

## metadata
knowledge_dimension: risk_calibration
difficulty: basic
