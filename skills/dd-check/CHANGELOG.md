# dd_check 版本更新记录

> 完整版本历史记录。优化Skill或回溯变更时读取此文件。

## 版本记录

**V4.2（2026-09-17）— Phase 1 Close-out**

- 异常处理表"T3 与 T2 结论矛盾→以 T3 为准"改为"新证据触发重新裁决（六维框架），T3 不自动获胜"：仅事实时点变化时旧结论标"已更新"并列示变更轨迹；同一时点事实冲突登记 contradiction_group、双源并列不选边
- 质量检查清单新增 evidence_registry 登记项：关键 ✅ 事实与 ⚠️ 冲突按 CONTRACT §2.5 分配 F/E 编号（claims + evidence，claim_id 均有命题定义）

**V4.1（2026-09-17）— 证据裁决对齐 CONTRACT §2.5（Wave 2 接口改造）**

- 铁律修正：删除"独立数据源与公司底稿不一致时，以独立数据源为准并标注差异"，替换为"按 evidence_resolution_framework 六维度裁决（不自动选边），差异显式登记 contradiction_group（CONTRACT §2.5 evidence_registry），不得静默覆盖"
- 同步消除独立源优先暗示：降级模式"证伪公司披露"改为"交叉验证与差异登记"；异常处理表"独立源与公司材料矛盾→以独立源为准"改为登记 contradiction_group + 六维度裁决、双源并列；CONTRACT 引用表与 Dossier 填充原则补 §2.5 登记动作
- 接口级修改：核查流程、四级标注、verification_table/pending_materials schema、CP/AC 均不变

**V4.0（2026-09-15）— 开源重构：过程管控型 → 验收契约型**

- 共享规范引用（S1/S3-S7/S9/S10/S12/S13）整体替换为 `../risk-workflow/CONTRACT.md` 单一契约（§1 数据总线/§2 Dossier/§3 最小 output.json/§4 检查点/§6 验收/§7 适配器/§9 启动自检）
- SKILL.md 内给出 **9 维交叉比对权威定义**（第 9 维=董监高画像，含比对要点）；knowledge-base/reference/dd_check_dimensions.md 为 8 维旧版，待补第 9 维
- 待核实事项清单统一为 `pending_materials.json`（02_dd_check/，与 CONTRACT §1 衔接表对齐；原 pending_items.json 名称并入），T3 后同步更新旧版 `04_risk_report/pending_materials.json`
- 风险信号传导标注保留 `signal_direction` + `affected_report_section` 两字段，删除 `suggested_action`、`confidence`（由下游自行推断）
- IMA 并行核查改写为"第二信源（可选）"，引用 CONTRACT §7.3，缺失即跳过并按 AC5 显式标注
- 删除：T3 循环上限 10 次；output.json 的 `qcc_cross_check.dimensions_covered` 自报字段（改 CONTRACT §3 最小 schema）；检查点 CP2.1/CP2.2 签名与阻断话术（改 CONTRACT §4.2 子确认 + CP2 主检查点）；启动前置检查（改 CONTRACT §9 一页自检）
- T3 结论翻转保护压缩为一句话规则（列入异常处理表）
- 脱敏：示例中真实公司名（4+1 处）与人名（3+1 处）替换为占位表述

**V3.2（2026-05-04）— 控制论复盘优化**
- output.json 新增 `qcc_cross_check.dimensions_covered` 字段，机械化验证"9维度至少1项"交叉比对规则（P1）
- dd_check_dimensions.md 从8维度升级为9维度，新增"董监高画像"维度，与SKILL.md同步（P2）
- 清理S4引用中遗留的 execution_mode 字段说明（P2）
- IMA并行核查路径从"可选"升级为"建议执行"，适用条件满足时应主动执行（P2）
- 异常与边界处理新增"T3结论翻转"场景：同一项连续翻转≥2次→暂停+告知审批人（P2）

**V3.1（2026-04-27）— IMA并行核查（V5.1升级）**
- 新增S12/S13共享规范引用
- 新增步骤2.5：IMA并行核查路径（T2/T3可选），对关键核查项向IMA知识库提问获取补充信息
- 核查表item结构增加 verification_sources 和 ima_notes 字段
- T2质量检查增加IMA并行核查检查项

**V3.0（2026-04-26）— 重构版**
- 引入 _shared_specs.md 共享规范引用（S1/S3/S4/S5/S6/S7/S9/S10）
- 交叉比对维度表外化至 knowledge-base/reference/dd_check_dimensions.md
- 精简结构：上下游关系→表格、执行模式→表格、步骤合并去冗余
- 所有功能细节完整保留

**V2.2（2026-04-26）— K2.6 review后 Agent 宿主落地优化（P1+P3）**
- P1：T1触发主体语义统一，由"dd_prep步骤2.5触发"修正为"dd_prep步骤3在内部调用，AI无需单独启动dd_check Skill"
- P3：dossier更新质量检查新增"冲突检测已执行"（遵循S5冲突检测规则，§12风险信号与§3/§5/§7/§9事实一致性已核对）

**V2.1（2026-04-23）— 风险信号传导标注增强**
- 新增"3.4 风险信号传导标注"：为⚠️❌📌项附加4维传导标注（signal_direction/affected_report_section/suggested_action/confidence）
- signal_direction判断规则：↑增强（新发现负面）/→稳定（确认无变化）/↓缓解（风险在收窄），与risk_report原则五联动
- 目的：让risk_report在批量更新时读取传导标注，更准确判断每个发现项的影响程度，减少事后修正
- 来源：某科技项目V0.1d→V0.3d工作流复盘

**V1.1（2026-04-13）— 三触发点架构+增量追加**
- 核心架构变更：从"单次执行"升级为"三触发点+增量追加"模式
- 新增三触发点：T1前期资料扫描（dd_prep期间）、T2清单回复核查（公司按清单提供）、T3补充资料核查（访谈/报告后发现需补充）
- T1：反向匹配模式（先有材料→判断覆盖清单项），输出 available_materials.json 供 dd_prep 避免重复要求
- T2：正向匹配模式（清单→材料→逐项核查），完整执行全部四步核查逻辑
- T3：增量核查模式（特定问题→针对性材料→验证），输出 delta 文件
- verification_table.json 改为持续累积（trigger_history + provided_at_trigger + deep_checked_at_trigger）
- pending_items.json 改为动态更新（discovered_at_trigger + resolved_at_trigger）
- 新增 available_materials.json 输出（仅T1），供 dd_prep 步骤5读取
- 启动对话流程更新：确认触发点类型+增量判断逻辑
- 质量控制检查点按触发点差异化拆分
- 执行模式说明补充：补充尽调模式与T3触发点的关系澄清

**V1.0（2026-04-12）— 从dd_interview模块A独立拆分**
- 从 dd_interview V3.5 模块A（资料核查）独立拆分为新Skill
- 核心能力：对照尽调清单+QCC缓存+行业研究，逐项核查公司底稿
- 四级标注体系：✅已提供+一致 / ⚠️已提供但不一致 / ❌未提供 / 📌需现场核实
- 交叉比对：企查查数据 vs 公司提供材料（8个维度）
- 输出：verification_table.json（核查表）+ pending_items.json（待核实事项清单）
- 支持三种执行模式：标准/加急/补充尽调
- 继承PDF/图像文件读取条件触发规则（PaddleOCR）
- 新增知识库引用指令（风控发现沉淀+行业专项检查库+案例学习笔记）
- 新增质量控制检查点（10项）

**V2.2→V3.0** — DRY重构（2026-04-26）
- 抽取共享规范S1/S3-S7/S9/S10至 `_shared_specs.md`（S2/S8用qcc_cache非直调QCC）
- 交叉比对维度表外化至 `knowledge-base/reference/dd_check_dimensions.md`
- 633行→约440行（压缩30%），零功能损失
