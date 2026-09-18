# Synthetic Eval 首轮运行报告（2026-09-17）

> 运行背景：Capability Phase 1 Close-out Patch 之后（Dossier 语义统一、赢家规则删除、authority gate 分级、claims 落点、公司法错句修正、orchestrator 同步）。
> 结论先行：**12/12 PASS**。

## 运行方法

- **执行者隔离**：每个 eval 的「场景+输入」抽取为独立文件（不含「期望行为/判定标准」章节），派发全新会话的执行子代理——执行者看不到标准答案，防测试污染。
- **执行者上下文**：按 eval 所属能力维度提供对应技能文件（legal-research 组：SKILL + authority_schema + CONTRACT §7.5；evidence 组：evidence_resolution_framework + CONTRACT §2.4/2.5 + dd-check；confidence 组：CONTRACT + report-review 双轴规则 + 评级参考；behavior 组：report-review / risk-report / authority chain 规则）。
- **裁决**：主会话对照各 eval 的判定标准逐项裁决，本报告为裁决记录。

## 逐项结果

| # | Eval | 执行者关键行为 | 判定 |
|---|------|--------------|------|
| 01 | law/amended 条号漂移 | L012→amended 保留旧条号与映射，新开 L013 引 2025 修订版第21条（holding 取适配器逐字原文），报告改挂新编号并注明修订 | ✅ PASS |
| 02 | law/repealed 废止法规 | L018→repealed 禁止引用，新开 L019 承载现行条例第33条并补「规定规模」适用条件，义务结论改条件化+未核验清单 | ✅ PASS |
| 03 | law/superseded 规则取代 | L021→superseded 完整记录取代关系，L022 新记录含版本年份+第12.1条+逐字原文，下游（矩阵/条款落实表）改挂，例外收窄差异显式进待复核 | ✅ PASS |
| 04 | law/practice vs statute | L027 由 exchange_rule 重定型 practice（confidence low），禁止进 Rule 段；新开 L028 成文规则支撑 Rule；Application 改「实践中一般…」口径 | ✅ PASS |
| 05 | evidence/registry lag | temporally reconcilable（决定维度 Temporal+Legal operativeness），按协议认定 35%、双源保留、工商变更进待办；无「以登记为准」选边 | ✅ PASS |
| 06 | evidence/oral vs written | 协议存续为工作口径（Authority/Legal operativeness/Corroboration），反向检查补充协议与处分权限，访谈降为线索保留不删除，补证方向登记 | ✅ PASS |
| 07 | evidence/BP vs audit | scope difference 前置排除伪冲突（Scope consistency 决定维度），F 命题拆分（2025实际✅/2026预测[BP声称]）分别呈现，无机械覆盖 | ✅ PASS |
| 08 | evidence/dual conflict | 六维平手→unresolved 双源并列 ⚠️，补证方向（备案版本/签署原件/司法鉴定），进 §12+§14，附加文件真实性红旗信号 | ✅ PASS |
| 09 | confidence/高影响低证据 | 双轴分离：等级按潜在风险封顶中🟡（原则一）+ certainty claimed/⚠️，条件化措辞，补证登记+重评级触发器；无断言、无静默删除 | ✅ PASS |
| 10 | confidence/单源陈述 | 两处公司自述不构成独立印证，F068 维持 claimed/[BP声称]，标签传导不升级，专利登记簿副本进 pending | ✅ PASS |
| 11 | behavior/unresolved 措辞 | 草稿判定不可用（静默选边+标签升级+无来源数字），改写为双源并列+「若甲/若乙」条件分支+自我声明条件化判断；矩阵补 confidence 与 evidence_dependency | ✅ PASS |
| 12 | behavior/R→L chain 审计 | L034 孤儿引用 FAIL + L041 amended FAIL + L036 正常项不误报；整体结论**不得通过 CP3**、退回 legal-research 补验；4 项修复路径+复验条件 | ✅ PASS |

## 关键验证点

本轮重点验证 Close-out Patch 修复的三处 contract drift 是否真正生效：

1. **Eval 12（旧规则冲突点）**：执行者正确应用了新的分级 gate——V0.xd 草稿 WARN 可迭代 / CP3·V1.0d 定稿无 effective authority chain 即 FAIL 不得过 CP3。旧版「待核验不判 FAIL」的后门行为未再出现。
2. **Eval 05（旧赢家表靶点）**：工商登记 vs 已交割协议场景，执行者走 temporal reconciliation 而非「第一优先源获胜」；六维裁决决定维度明确指出。
3. **Eval 07（机械覆盖靶点）**：BP 预测 vs 审计实际数，Scope consistency 前置排除伪冲突，未出现「以审计为准故 2026 营收不成立」式错误。

## 局限说明

- 每用例单次运行（非多次采样）；执行者为独立子代理而非完整 6-Phase 流水线，验证的是**规则遵从行为**，不等价于端到端项目回归。
- 新开 L 编号与 eval 示例编号不同（如 L013 vs 示例 L031）——判定标准不锁定具体编号，编号纪律（不重排不复用）本身被执行。
- 下一步以真实项目跑一轮完整流程，验证 authority chain 与证据裁决在实践中的衔接。
