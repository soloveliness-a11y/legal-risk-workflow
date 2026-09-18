# dd_prep 版本更新记录

> 完整版本历史记录。优化Skill或回溯变更时读取此文件。

## 版本记录

**V6.2（2026-09-18）— 启动与初筛减法**

- Step 1.2 风险假设的"假设是否充分"子确认取消单独停顿：假设摘要随 CP1 呈报一并审批，信息回补由 1.4.2 最低信息集判断把关
- CP1 呈报项增补推断与缺省字段（investment_stage / project_type 等，含依据）
- 初筛卡单文件化：脚本新增 --format json，项目内只落盘 risk_screening_card.json（llm_supplement 预置空位，LLM 在同一文件补写行业专项指标与综合判断）；md 卡片按需渲染，不再作为落盘产物

**V6.1（2026-09-17）— P1 精简：按三分类标准去除通用步骤指令，领域方法论零损失（469 行 → 352 行，-25%）**

- **三分类标准**（DOMAIN 领域知识 / CONTROL 控制规则 保留；GENERIC 模型通用步骤 删除）：GENERIC = 2026 年强模型天然会做的步骤编排
- **删除/压缩 GENERIC**：启动问卷 6 字段 + 输入表 → 紧凑字段行；4 步 DAG ASCII 块 → 单行流程；§9 启动自检详细展开 → 一行指针；各 Step 开头"动作"编排行；qcc_scan / industry_research 调用参数 code fence → 单行（保留"必须全称，简称返回空"等 gotcha）；risk_screener 命令 6 行 → 1 行；"本步骤继续读取 X 传给 Y"类编排；1.4.2 分支代码块 → 行文；Dossier 交付自检清单与填充表去重；下游衔接树 → 紧凑列表；资源索引 5 行 → 3 行；附录 B 时机编排压缩；各 Step 重复的"更新 Dossier 与 project_log"统一到 Dossier 初始化节
- **保留全部 DOMAIN 资产**：17 模块清单、行业专项表、轮次差异化（附录 A 整块）、CoT 映射（整块）、前轮条款五级优先级、第三方尽调报告三规则、内外双版本、降级措辞纪律、最低信息集三文件、量化分层、董监高画像扩展触发条件、材料预处理命名/禁 OCR 规则、风险假设模板与生成原则
- **CONTROL 语义不变**：CP1 阻断、§4.2 子确认、output.json schema、L3 异常升级、轻量模式降级、Dossier 时点与填充分工

**V6.0（2026-09-15）— 开源重构（Phase 2 契约化收敛，932 行 → 456 行，方法论零损失）**

- **删除 V5.1 控制论补偿层**：启动前置三查（→CONTRACT §9 一页自检）、CoT 计数门槛（映射≥5/遗漏≥3）与 analysis_checker.py 脚本后验、分支点决策日志双份模板（并为一行日志）、CP1.2/CP1.4 签名模板、Step 1.4 回环上限 max_loop、qcc_cache schema_version 校验话术、research_mode 并发/串行约束及 S11 引用、旧步骤映射表/9 项优化清单/加急移除说明等版本残留、重复标题
- **通用约束收敛到 [CONTRACT](../risk-workflow/CONTRACT.md)**：CP1 审批（§4.1，保留阻断语义）、Step 1.2 假设充分性降为子确认（§4.2）、output.json 最小 schema（§3）、Dossier 规则（§2）、验收 AC3/AC5（§6）
- **修复 findings_summary 零产出根因**：统一引用 §7.1 findings_summary.json 契约（category/item/severity/fact/source_ref），替代旧 findings_summary.md 路径
- **保留全部核心资产**：4 步 DAG、17 模块清单模板、风险假设生成（3-5 个/优先级/溯源）、CoT 来源→清单项+置信度映射、轮次差异化（附录 A）、前轮特殊条款优先级与问题跟进、清单内外双版本、降级措辞纪律（"风险不可评估"）、risk_screener.py 确定性初筛、最低信息集判断标准、L3 异常升级；脱敏：人名→审批人（16 处）、路径 {workspace} 占位符化

**V5.1（2026-05-04）— 控制论复盘9项优化（V7.2普适性落地）**

> 触发：workflow-retro 控制论五维度诊断，综合合规度59%→优化后预期>85%

- **P1 (P0) Dossier存在性断言**：启动前置检查Step 0，dossier不存在→模板初始化+告警；初始化失败→output.json.status=failed（映射V7.2 O2）
- **P2 (P0) CoT校验脚本化后验**：新增analysis_checker.py，6项自动校验（映射≥5/自洽5项/遗漏≥3/排除理由/字段完整/置信度），🔴阻断项未通过不得继续（映射V7.2 O1）
- **P3 (P1) skill_version校验**：启动前置检查，output.json.skill_version≠5.1→告警+差异对比（映射V7.2 O4）
- **P4 (P1) 分支点硬编码日志模板**：Step 1.2/1.4分支决策增加结构化日志（决策/依据/替代方案/选择理由），写入project_log.md（映射V7.2 O3）
- **P5 (P1) 检查点签名机制**：CP1.2/CP1.4增加签名模板（确认人/时间/意见/修改要求），CP1.4未签名→output.json不得标记completed（映射V7.2 O5）
- **P6 (P2) Step 1.4回环上限**：max_loop=2，超过→强制进CP1.4由审批人决定；迭代计数器写入project_log.md
- **P7 (P2) L3异常升级定义**：QCC+前轮+公司材料全缺失→L3暂停，告知审批人"项目信息严重不足"
- **P8 (P2) 行业研究降级措辞修正**："标注[推断]无行业特殊风险"→"标注📌待核实：行业风险不可评估，需补充研究"（消除假安全感）
- **P9 (P2) qcc_cache schema版本校验**：Step 1.1.2读取qcc_cache.json前校验schema_version，旧版格式→告警+建议增量补充

**dd_prep特有问题（V7.2未覆盖，已记录待后续处理）：**
- findings_summary.md零产出：需验证qcc_scan Skill的findings_summary输出路径
- available_materials.json路径不一致：V2.3时代产物，启动前置检查已覆盖检测
- 旧版项目缺risk_hypotheses.md：启动前置检查已覆盖检测

**V5.0（2026-04-30）— DAG硬编码4步拆分（V7.0升级）**
- **架构升级**：从8步线性流程重组为4个独立可调用的DAG节点
- **Step 1.1 知识积累**：原步骤2（qcc_scan）+ 步骤4（industry_research）+ 步骤2.6（risk_screener）+ 步骤3（T1轻扫描）合并
- **Step 1.2 风险假设**：原步骤2.5（风险假设生成）独立为可调用节点
- **Step 1.3 尽调清单**：原步骤5（CoT校验）+ 步骤6（清单生成）合并
- **Step 1.4 访谈提纲**：原步骤7（访谈提纲）独立为可调用节点
- **Dossier实时更新**：遵循S5字段级来源标注+确定性标签强制
- **操作日志**：遵循S10，每个Step完成后追加结构化日志
- **分支点设计**：Step 1.2后（假设是否充分）+ Step 1.4后（是否需要补充核查）
- **保留向后兼容**：所有产出文件名不变，output.json schema不变，下游衔接不变

**V4.0（2026-04-28）— 能力拆分+独立化（V6.1升级）**
- **能力拆分**：步骤2（QCC扫描）拆出为独立能力Skill `qcc_scan`（~130行），可跨Phase 1/2/3/6调用
- **能力拆分**：步骤4（行业研究）拆出为独立能力Skill `industry_research`（~160行），可跨Phase 1/2/3调用
- **编排角色**：dd_prep从"全流程执行"变为"调用独立能力+本地步骤"
- 步骤2改为调用qcc_scan Skill（传入company_name/scope/output_dir，获得qcc_cache.json+findings_summary）
- 步骤4改为调用industry_research Skill（传入industry/output_dir/research_mode等参数，获得research_*.md+sources_*.json）
- 共享规范引用调整：S2/S8移至qcc_scan承载，S3/S11/S12移至industry_research承载
- 质量检查新增qcc_scan/industry_research调用成功检查
- 产出文件名不变，output.json schema不变，下游衔接不变
- 730行→约580行（减少约20%）

**V3.1（2026-04-27）— IMA集成+风险假设（V5.1升级）**
- 新增步骤2.5：风险假设生成（risk_hypotheses.md），基于项目特征+QCC数据生成3-5个风险方向假设
- 步骤4改造：每路研究输出 sources_*.json（原始URL+标题+检索关键词归档）
- 新增步骤4.5：IMA知识归档，调用 ima_kb_archive.py 将研究URL导入知识库
- 引用规范表增加S13专项调研引用
- 执行流程图更新：步骤2→步骤2.5→步骤3
- output.json research_files 增加 risk_hypotheses.md
- 质量检查增加 risk_hypotheses.md 检查项
- 下游衔接增加风险假设传递路径

**V3.0（2026-04-26）— DRY重构**
- 全面DRY重构：12个共享规范引用（S1-S12），替换内联重复内容
- QCC手动fallback命令外部化至 knowledge-base/reference/qcc_manual_fallback.md
- 并发研究子代理详细YAML压缩为核心要点，详细规则由S11承载
- IMA调用详情由S12承载
- output.json schema由S4承载
- Dossier初始化由S5承载
- 1337行 → 约580行（压缩约57%），零功能损失

**V2.12（2026-04-26）— K2.6 review后 Agent 宿主落地优化（P1+P4）**
- P1：步骤3"已有资料轻扫描"语义统一，明确T1在dd_prep内部执行（不单独调用dd_check Skill），边界为"仅做材料清单登记+反向匹配，不做深度核查"
- P4：CoT校验（analysis_log.md）增强：映射表新增"置信度"列（⭐5级标准）、新增"遗漏识别"小节（主动扫描潜在遗漏项）、新增"整体置信度评估"小节（最大不确定项+建议关注）
- 步骤8质量检查新增"冲突检测已执行"（遵循S5冲突检测规则）

**V2.11（2026-04-13）— 清单内外双版本+Word生成统一调用md_to_docx_enhanced.py**
- 清单增加内外双版本规则：外部版（发给公司）不含风险等级/核实方式/重点关注等内部字段，内部版（风控标注版）保留全部字段
- external版格式：模块分节+列表项，清洁简洁；internal版格式：表格6列（序号/资料名称/风险等级/核实方式/重点关注/来源）
- 两版共享同一份checklist_data.json结构化数据（增加risk_level/verification_method/special_attention字段）
- Word生成统一调用md_to_docx_enhanced.py（外部版mode=normal，内部版mode=enhanced）
- 输出1从单文件改为双文件：checklist_external.docx + checklist_internal.docx
- 访谈提纲Word生成也统一调用md_to_docx_enhanced.py
- 质量控制检查点新增3项（双版本生成/md_to_docx调用/访谈提纲调用）
- 根因：对外清单一律不含风险等级/核实方式/重点关注等内部字段
- 格式基准：参考三个不同行业实际项目的清单格式归纳

**V2.10（2026-04-13）— 已有资料轻扫描+清单去重**
- 新增步骤2.5：已有资料轻扫描（触发dd_check T1），输出available_materials.json
- 步骤5补充清单生成增加去重逻辑：读取available_materials.json，标注"已有资料勿重复要求"
- 清单输出JSON格式更新：items从字符串数组改为对象数组，增加status/available_file/note字段
- 新增清单去重规则：[已有-待核查]/[需补充]/[已有-需核实]三级标注
- 流程图更新：步骤2和步骤3之间插入步骤2.5
- 质量控制检查点新增3项（轻扫描执行+清单去重+标注格式）
- 与dd_check的数据衔接新增：dd_check T1回传available_materials.json
- 根因：投资经理在尽调准备阶段可能已获取部分公司资料，清单需避免重复要求

**V2.9（2026-04-11）— P2优化项修复**
- P2-3：步骤3新增"跨境项目境外法律评估"条件触发（境外业务≥20%或有实际经营境外子公司），输出research_04_crossborder.md（FDI审查/数据跨境/出口管制/行业准入4项评估）
- P2-3：步骤5.3行业专项合规模块表增加"跨境/出海"专项行

**V2.8（2026-04-11）— P1优化项修复**
- P1-1：步骤1解析维度表增加"前轮投资人权利状态"维度（回购/对赌/反稀释/一票否决/最惠国），标记已触发/即将到期的特殊权利
- P1-6：qcc_cache中findings_summary从字符串改为结构化数组，每项含category/finding/severity/source_tool四字段，支持后续Skill分类筛选

**V2.7（2026-04-11）— P0优化项修复**
- P0-3：加急模式步骤3从"跳过行业研究"改为"快速行业扫描"（单次web_search+精简版research_01_quick.md），天使项目同步适用轻量版（仅查资质+IP/竞业）

**V2.6（2026-04-10）— 子代理策略优化：顺序研究为默认**
- 步骤3行业研究默认改为主进程顺序执行（research_mode="顺序"），3路研究依次由主进程完成，成果直接落盘，0失败率
- 子代理并发降级为可选模式（research_mode="并发"），仅非高峰期+网络良好时使用
- 新增research_mode参数：控制步骤3执行方式（"顺序"默认 / "并发"可选）
- 新增子代理结果强制校验：并发模式下子代理返回后必须验证文件是否实际写入，未写入则主进程增量补做
- 根因：Agent 宿主环境下子代理存在高峰期响应慢、回灌失败问题，导致双重token消耗

**V2.5（2026-04-09）— 清单模块扩充 + CoT校验 + Token优化**
- 清单标准模块扩充：12模块58项 → 17模块，新增商业贿赂与反腐（模块5）、劳动人事细节（劳务派遣/外包/保密协议覆盖率/竞业有效性，模块9）、职务发明专项（模块13）、数据合规细化（数据出境/算法备案/重要数据，模块14）、国资/外资/VIE专项（模块15）、重大合同关键条款核查（CoC/排他/终止/转让，模块16）、境外子公司合规（模块17）
- 环保/安全生产模块扩充：增加安全生产事故及整改、危废处理合规、碳排放/ESG（模块8）
- 股东和实控人模块扩充：增加创始人个人对外担保/关联负债、涉及的其他企业同业竞争（模块2）
- 行业专项表细化：从笼统描述改为具体核查清单，新增消费品/餐饮行业
- 新增步骤4: CoT思维链强制校验（analysis_log.md结构化映射表+5项自洽检查）
- 新增大文件文本预处理：doc_preprocessor.py脚本，legal_risk模式按关键词筛选
- 新增复杂表格处理规则：xlsx Skill替代OCR，PDF复杂表格截图+人工确认
- 企查查JSON处理优化：保留本地全量数据+仅传findings_summary摘要给清单/访谈步骤
- 流程图更新：增加步骤4 CoT校验环节，步骤5/6重新编号
- 质量控制检查点新增6项

**V2.4（2026-04-08）— 实测复盘优化**
- 子代理研究成果落盘：3路子代理输出必须保存为本地.md文件（research_01/02/03.md），供下游Skill复用
- 并发策略精简：5路→3路核心（IPO+风险回溯合并 / 监管+政策 / 微信+小红书），减少阻塞风险
- 降级机制：子代理超时/失败不影响其他路，max_turns=5限制，研究不充分时标注提示
- PDF读取规则修正：仅扫描版PDF调PaddleOCR，普通PDF直接read_file，增加判断流程图
- OCR结果保存规范：OCR输出必须存为.md文件，供后续Skill直接读取
- output.json增加research_files字段，索引研究文件路径
- 下游衔接扩展：research_*.md供dd_interview/risk_report/report_review引用
- 质量控制检查点新增4项

**V2.3（2026-04-08）— PaddleOCR 强制调用规则**
- 新增 PDF/图像文件读取规则：禁止大模型直接读取扫描 PDF，强制调用 PaddleOCR-VL API
- 适用于：小预审材料、前轮尽调报告、公司底稿、企查查截图等
- 配置 PaddleOCR-VL MCP Server 到 mcp.json

**V2.2（2026-04-08）— 信息源扩展 + 启动流程规范化**
- 新增启动对话流程（材料收集步骤）
- 步骤3并行研究扩展为5路子代理：新增微信公众号补强搜索（必选）、小红书信息补强（可选）
- 小红书搜索使用 xhs-search-workflow Skill，含风控调用规则（频率限制、错误处理）
- 流程图更新，反映5路并发架构

**V2.1（2026-04-08）— V3.0工作流适配**
- 修正QCC路径为工作区目录
- 新增加急模式（跳过并行研究）
- 新增风险初筛卡输出

**V2.0（2026-04-06）— 基于实操经验全面重构**
- 重构为可执行的尽调启动引擎
- 新增按轮次差异化策略（天使精简/成长期全面/Pre-IPO上市核查）
- 新增企查查预扫描流程
- 新增行业研究 & IPO问询焦点研究（子代理并发）
- 新增前轮问题跟进核实机制
- 新增行业专项合规模块（AI/芯片/医疗/SaaS等）
- 新增访谈提纲生成（仅法律方向，与投资团队分工）
- 新增前轮特殊条款审查优先级规则
- 集成 docx 文档生成 Skill
- 补充清单结构：问题跟进 + 标准基底增补 + 行业专项

**V1.0（2026-03-30）— 基础框架**
- 框架定义
- 尽调清单模板
- 访谈提纲框架

---

**核心价值：将尽调准备从"发全量模板"升级为"精准的补充清单 + CoT逻辑校验 + 法律访谈聚焦 + 行业风险预判 + Token高效利用"，贴合风控律师实操流程。**

**V3.0** — DRY重构（2026-04-26）
- 抽取共享规范S1-S9/S11/S12至 `_shared_specs.md`（S10自备质量清单保留内联）
- QCC手动fallback外化至 `knowledge-base/reference/qcc_manual_fallback.md`
- 1337行→约599行（压缩55%），零功能损失
