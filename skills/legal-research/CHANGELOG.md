# legal_research 版本更新记录

> 完整版本历史记录。优化Skill或回溯变更时读取此文件。

## 版本记录

**V1.0（2026-09-17）— 初始版本：法源验证能力独立成技能**
- 定位：验证法律命题有没有现行、适用、足够权威的依据，构建 authority chain（R 编号→L 编号→条文逐字原文）；与 industry_research 平行（后者研究行业，本技能验证 authority）
- 法源适配器 3 路（CONTRACT §7 模式，语义统一）：远答法规库 MCP（语义检索+条文逐字）/ 企查查法规库 MCP（关键词+批量引用核验）/ 手工核验模式（默认可用，零外部依赖）
- authority_record schema（14 字段）+ proposition_id（L001…）稳定编号，供 risk_report 风险项 `legal_propositions` 字段引用
- 五类法源分类与使用边界：practice 类（内部经验/历史模式）不得写成法律依据、不得作为 authority 引用
- 执行流程 Inputs→Checks→Outputs→Acceptance：四步核验（检索→现行有效性→条文逐字→实质匹配）；未核验项清单显式化
- 产出落盘 `projects/{项目}/legal_authority.json`（项目级共享，跨 Phase 复用）
- 降级（AC5）：适配器不可用切手工核验（source_ref=manual）；无法核验标 uncertain+low，不得作为法律结论依据；知识库 last_verified 过期（默认 90 天）触发重验
- 契约引用：§7 适配器语义 / §6 AC3 来源标注扩展（法条引用须有 authority_record 支撑）/ AC5 降级显式化 / §3 output.json 最小 schema
