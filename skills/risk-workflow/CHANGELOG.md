# risk-workflow 版本更新记录

> 完整版本历史记录。优化Skill或回溯变更时读取此文件。

## 版本记录

**V8.1（2026-09-17）— Phase 1 Close-out：全局语义同步**

- 能力技能数 9 → 10：能力清单表新增 legal_research（主战场 Phase 3，可调用 Phase 4/5）；触发词补 legal_research
- 全局契约表述"Dossier 单一数据源"改为"Dossier canonical working view + 证据链登记"（CONTRACT §2 语义迁移）；知识库加载描述 6 → 7 大风险主题

**V8.0（2026-09-15）— 开源重构：契约化收敛**

- 全部共享约束收敛至 [CONTRACT.md](./CONTRACT.md)：删除 S1-S16 引用网、16 检查点详表与签名模板、启动 8 步自检展开、output.json 校验话术、场景判断六字段模板、能力清单来源列版本硬编码
- 定位放松为"阶段主干固定为默认路径，分支点模型建议调整，主检查点人工审批"；检查点收敛为 4 主 CP + 可选子确认
- 正文 888 → 171 行；保留 6 阶段业务链、三模式语义、调用原则、风险评级核心原则、数据飞轮，方法论零损失
- 脱敏：人名统一改"审批人"（26 处），路径统一 `{workspace}` 占位符；核查维度口径统一为 9 维

**V7.3（2026-05-04）— 全技能生态系统审查与统一**

> 触发：risk-workflow 全技能生态系统审查报告（22项问题）→ 执行全部优化方案

- **C1 修复**：dd_prep output.json skill_version "5.0"→"5.1"（版本硬编码错误）
- **C2/A1/A2 修复**：统一检查点编号体系为 CP{Phase}.{序号}：
  - 主检查点 CP1-CP4 保持不动，新增子检查点映射表
  - dd_interview CP-A/CP-B → CP2.3/CP2.4
  - txn_docs CP-A/CP-B → CP4.1/CP4.2
  - post_invest_check CP-4/CP-5 + CP-A/CP-B → CP4.3/CP4.4（消除双重体系）
  - dd_check [检查点A/B] → CP2.1/CP2.2
  - report_review CP-3a → CP3.3
  - risk_report CP-3.0/CP-3.6 → CP3.1/CP3.2
- **S9 重写**：检查点定义从3个扩展为完整16个（4主CP + 12子CP），增加签名统一模板
- **S2 更新**：qcc_scan basic scope 明确为11项（第一梯队8项 + IP/诉讼3项升为必调）
- **S5 更新**：新增 V7.3 精简原则，要求子Skill Dossier更新只描述差异化内容
- **C4 修复**：风险评级核心原则表增加"行业特异性例外"维度
- **A4 修复**：project_log 结构新增"场景判断记录"章节
- **A3 修复**：dd_check T1 表格明确标注"由dd_prep代理执行"
- **A8 修复**：预期产出文件清单 Step 1.3 补充 checklist.json + analysis_log.md
- **O1 修复**：CHANGELOG 删除重复的 V5.0 条目
- **O2 修复**：dd_check 引用路径从相对路径改为绝对路径
- **O3 修复**：report_review 扩展检查清单 8a→9，11项→12项
- **O6 修复**：能力清单表 dd_prep 来源列补充"V5.0 DAG重构拆分"
- **O7 修复**：SKILL.md 标题 V7.1→V7.2
- **签名模板统一**：全部检查点签名改用 Markdown 格式，遵循 S9 统一模板
- **涉及文件**：SKILL.md / CHANGELOG.md / _shared_specs.md / dd_prep / dd_check / dd_interview / risk_report / report_review / txn_docs / post_invest_check

**V7.2（2026-05-04）— 控制论复盘优化（机械化约束升级）**

> 触发：workflow-retro V1.0 控制论五维度诊断 → 🔴×3 → 进入Step 6执行优化

- **O2·Dossier存在性断言**：启动流程增加project_dossier.md存在性检查，缺失→从模板初始化+标注[重建]+告警审批人
- **O1·跨章一致性检查脚本**：新增`scripts/tools/consistency_checker.py`，Step 3.6从"LLM自觉执行"升级为"脚本强制执行+LLM审查"模式。支持分章md和完整报告md自动拆分
- **O4·output.json版本校验**：启动流程增加skill_version与当前SKILL.md主版本号匹配检查，版本漂移→告警
- **O3·分支点记录强制化**：4个分支点（Step 1.2/1.4/2.3/4.2）增加硬编码日志模板，决策后必须写入project_log.md
- **O5·检查点签名机制**：4个检查点（CP1-CP4）增加签名模板，审批人确认后必须写入project_log.md（含确认人/时间/意见）
- **O6·Phase目录缺失告警**：启动流程增加Phase目录完整性检查，日志Phase > 实际目录深度→告警
- **根因修复**：观测器与执行器分离——关键约束从"文档规则"升级为"脚本强制"，解决LLM三位一体开环控制问题
- **涉及文件**：SKILL.md / scripts/tools/consistency_checker.py（新增）

**V7.1（2026-05-02）— 轻量优化（质量优先）**

- **Dossier更新强制化**：S5增加前置阻断规则（output.json生成前必须先完成Dossier更新），S10标记为🔴阻断项
- **DAG步骤验证机制**：启动流程增加步骤验证逻辑（预期产出文件存在性检查），新增各步骤预期产出文件清单
- **确定性标签体系统一**：废弃 Y/P/!|X/[BP]/[Inference] 缩写格式，统一为 emoji+中文（✅已确认/📌待核实/⚠️不一致/❌未提供/[BP声称]/[推断]）
- **review_findings下游消费显式化**：dd_check T3 + dd_interview 增量访谈增加 review_findings.md 作为显式输入源
- **pending_materials联动硬编码化**：dd_check T3 中 pending_materials.json 联动从描述性文字提升为硬编码步骤
- **post_closing_obligations字段名对齐**：txn_docs 输出字段名（协议约定期限/当前状态/逾期风险）与 post_invest_check 台账格式一致
- **文档过时项修复**：dd_check skill_version 3.0→3.1 / post_invest_check MCP→CLI / risk_report S2锚点修复 / commands/start-project V4.0→V5.0
- **脚本路径规范化**：全部子Skill中 `scripts/xxx.py` → `scripts/tools/xxx.py`（兼容入口），S14目录结构更新为 `tools/`
- **knowledge-base VERSION.md**：新增知识库版本标记文件，S1加载步骤增加 VERSION.md 读取
- **涉及文件**：_shared_specs.md / SKILL.md / dd_check / dd_interview / dd_prep / risk_report / report_review / txn_docs / post_invest_check / industry_research / qcc_scan / commands/start-project.md / knowledge-base/VERSION.md

**V6.1（2026-04-28）— dd_prep能力拆分**
- **能力拆分**：dd_prep的QCC扫描拆出为独立能力 `qcc_scan`（~130行）
- **能力拆分**：dd_prep的行业研究拆出为独立能力 `industry_research`（~160行）
- 能力总数 7→9
- 架构图更新：Phase 1/2/3/6 调用能力列表更新
- 能力清单表更新：新增"来源"列，标注V6.1拆出
- 数据衔接协议更新：新增qcc_scan/industry_research产出映射
- Phase调度表更新：各Phase可调用能力表新增qcc_scan/industry_research
- _shared_specs.md更新：S2适用范围从dd_prep改为qcc_scan，S8说明更新
- dd_prep V3.1→V4.0：编排角色，调用独立能力

**V6.0（2026-04-28）— Phase+Capability架构升级**
- 从Pipeline（线性流水线）升级为Phase+Capability（6阶段×7能力动态调度）
- 新增project_log.md执行日志机制
- risk-workflow角色重定义：从"架构说明书"变为"阶段调度器"
- 7个子Skill从流程节点变为独立能力

**V5.1（2026-04-27）— IMA集成升级**
- S12重写：IMA从辅助搜索升级为三模式系统（LLM问答/URL归档/关键词搜索），含详细调用模板和各Skill适用场景
- S6补充：扫描件读取增加IMA优先路径（四级fallback：IMA→paddleocr→MCP→手动）
- S10更新：新增4项质量检查（sources_*.json/risk_hypotheses.md/IMA归档/专项调研）
- 新增S13：专项调研规范，定义dd_prep→risk_report间定向法律分析环节
- 共享规范表扩展至S1-S13
- dd_prep V3.0→V3.1：步骤2.5风险假设+步骤4 sources_*.json+步骤4.5 IMA归档
- dd_check V3.0→V3.1：步骤2.5 IMA并行核查路径
- 新增脚本：scripts/ima_kb_archive.py（URL归档工具）
- 新增脚本：scripts/ima_kb_query.py（IMA知识库AI问答）

**V5.0（2026-04-26）— DRY重构**
- 全面DRY重构：12个共享规范（S1-S12）抽取到 `_shared_specs.md`
- 主Skill仅保留引用表，从958行压缩至约330行（66%），零功能损失
- 子Skill版本同步更新至DRY重构版

**V4.4（2026-04-26）— K2.6 review后 Agent 宿主落地优化（P3）**
- P3：S5"项目全景档案全局规则"新增"Dossier冲突检测规则"子节，定义5类检测范围（元信息一致性、风险信号与事实一致性、风险等级与完备度匹配、待办同步、时间线逻辑）和3级处理方式（严重冲突提示确认/轻微冲突仅标注/不自动修正）

**V4.3（2026-04-15）— P1边界条件覆盖+P2检查点设计+P3 Frontmatter优化**
- P1-1: OCR三级fallback（PaddleOCR主→备用OCR→降级read_file+用户手动补充）
- P1-2: Markdown存档防丢失规则（每个子Skill必须先存md再转docx，Word失败时md作备选交付物）
- P1-3: 子代理失败禁止自动重试，改为用户三选一决策（主进程完成/手动重试/跳过）
- P1-4: QCC API降级路径（缓存检查→用户手动上传企查查报告→标注数据来源限制）
- P2: 三个关键检查点（dd_prep→dd_check清单确认、risk_report风险方向确认、report_review不通过用户三选一）
- P3: Frontmatter description精简（200字→概念说明+触发词列表）、V3.x变更日志移至CHANGELOG.md
- 全局质量检查清单更新：新增Markdown存档检查项、OCR fallback检查项

**V4.2（2026-04-14）— P0-P5六项优化**
- dd_interview V3.5 拆分为 dd_check V1.0（资料核查）+ dd_interview V4.0（访谈纪要）
- Skill链从6个扩展为7个
- 目录编号重新排列：01_dd_prep/02_dd_check/03_dd_interview/04_risk_report/05_report_review/06_txn_docs/07_post_invest/
- 数据衔接协议更新：新增dd_check字段映射（verification_table→risk_report, pending_items→dd_interview）
- 补充尽调模式更新：dd_check和dd_interview都是可选操作
- 加急模式更新：Skill编号随新架构调整
- 全局架构图更新：新增dd_check节点

**V3.6（2026-04-11）— P2优化项修复**
- P2-3（dd_prep V2.9）：步骤3新增"跨境项目境外法律评估"条件触发（境外业务≥20%或有实际经营境外子公司），步骤5.3增加跨境专项行
- P2-4+P2-10（risk-workflow V3.6）：新增"知识库维护规则"段落，每5个项目触发审查（风控发现沉淀+行业专项库+writing_patterns+术语表）
- P2-7（post_invest_check V3.3）：控制表更新升级为"核心风险自动输出"，输出JSON增加control_table_updates结构化字段
- P2-8（dd_interview V3.5）：新增"转写稿来源适配"段落，通义听悟纠错规则（专业术语/公司名/人名/技术名词/数字金额）
- 排除项：P2-1（天使做全量研究）、P2-2（加急不降级复核）、P2-5（手动触发案例笔记）、P2-6（不需要投资经理摘要）、P2-9（手动跟踪回购）
- 子Skill版本同步：dd_prep V2.8→V2.9, dd_interview V3.4→V3.5, post_invest_check V3.2→V3.3

**V3.5（2026-04-11）— P1优化项修复**
- P1-1（dd_prep V2.8）：步骤1解析维度表增加"前轮投资人权利状态"维度
- P1-3（report_review V3.2）：第一层AI自查增加第6项"风险矩阵完整性校验"
- P1-4（txn_docs V3.2）：新增4.3节"前轮权利保全校验表"（模式二必选输出）
- P1-5（post_invest_check V3.2）：法律台账新增"陈述保证监控清单"子表
- P1-6（dd_prep V2.8）：findings_summary从字符串改为结构化数组
- P1-7（report_review V3.2）：新增步骤5.1"大预审风险摘要"+步骤5.2"投委会Q&A预案"
- P1-8（post_invest_check V3.2）：条件分支扩展退出触发（回购行权/股权转让/上市退出）
- P1-10（report_review V3.2）：补充资料闭环增加升级标准（≥3个调整/新风险类型/结论变化）
- P1-11（txn_docs V3.2）：输入增加report_review.conditions和review_comments为必填
- P1-12（risk_report V3.5）：风险评级增加"原则四：行业特异性例外"（6个行业不降级事项）
- 子Skill版本同步：dd_prep V2.7→V2.8, report_review V3.1→V3.2, txn_docs V3.1→V3.2, post_invest_check V3.1→V3.2, risk_report V3.4→V3.5

**V3.4（2026-04-11）— P0优化项修复**
- P0-1：补充尽调回路定义统一：主Skill与dd_interview统一为"增量模式"（追加补充专节，非独立重做），新增操作协议（补充范围+不重做已有纪要）
- P0-3：加急模式行业研究从"跳过"改为"快速扫描"（单次web_search+精简版research_01_quick.md约200行），同步更新主Skill加急描述

**V3.3（2026-04-10）— 知识库体系整合优化**
- risk_report SKILL瘦身：20个案例笔记迁至knowledge-base/案例学习笔记/，1464行→628行
- 风控发现沉淀主题化重构：63类编号→6大主题
- 行业专项检查库去重合并：24个模块→16个模块
- 术语表分层：A节通用+B节行业
- 5个Skill增加知识库引用指令
- Skill版本记录拆分：完整历史迁至CHANGELOG.md
- 保留法律法规索引和QCC查询索引

**V3.3（2026-04-09）— 目录架构重构：两层架构**
- 新增共享资源层：templates/（交易文件/风控报告/清单/访谈模板）、knowledge-base/（术语表/行业专项/法规索引/风控沉淀/QCC索引）、scripts/（doc_preprocessor/md_to_docx/qcc_cache_manager）、commands/（4个快捷命令）
- 项目目录增加 00_raw/（原始输入材料归集区）和 99_archive/（项目归档区）
- 项目目录增加 02_dd_interview/transcripts/（访谈转写稿子目录）
- 项目目录增加 05_txn_docs/ 完整5份文件（股权转让协议/股东名册/出资证明书）
- Skill引用路径统一：txn_docs模板→templates/交易文件模板/、dd_prep行业库→knowledge-base/行业专项检查库/、risk_report大纲→templates/风控报告模板/
- 脚本路径统一：doc_preprocessor→scripts/、新增md_to_docx和qcc_cache_manager

**V3.2（2026-04-09）— 同步dd_prep V2.5更新 + 全局架构修正**
- 同步dd_prep V2.5：CoT思维链强制校验（analysis_log.md）、清单模块扩充（17模块）、大文件文本预处理脚本、复杂表格xlsx处理规则、企查查JSON保留本地+仅传发现项摘要
- 修正全局架构流程图：左侧序号去重（01-08递增）、左侧改为投资经理流程名称（含投资建议书阶段标注）、右侧改为风控律师流程名称+对应Skill标注、补充大预审/投委会等无Skill环节的说明

**V3.1（2026-04-09）— 子Skill版本同步 + 全局规则更新**
- 同步6个子Skill版本号至最新（dd_prep V2.4, dd_interview V3.3, risk_report V3.2, report_review V3.1, txn_docs V3.1, post_invest_check V3.1）
- 新增 PaddleOCR 条件触发全局规则（替代原"强制调用"描述），明确普通PDF可直接读取
- 新增 research_files 数据衔接（dd_prep→dd_interview/risk_report/report_review）
- 更新项目文件目录结构（增加research_*.md和*_ocr.md）
- 更新数据衔接字段映射表（增加research_files等3条新映射）
- 更新子Skill描述对齐各Skill最新版说明
- 更新全局质量检查清单（新增3项）
- 更新全局架构流程图（反映最新版本号和research_files输出）

**V3.0（2026-04-08）— 架构优化版**
- 主 Skill 瘦身为指挥官角色，删除与子 Skill 重复的内部流程描述
- 新增三种执行模式：标准/加急/补充尽调
- 新增补充尽调回路（report_review 不通过时回到 dd_interview）
- 新增项目终止备忘录流程
- 统一数据衔接协议，新增字段映射表
- 统一项目文件目录结构（基于工作区）
- 统一输出 JSON Schema
- 统一 Word 文档生成技术规范
- 修正 QCC 缓存存储路径

**V2.1（2026-04-06）**
- dd_prep 升级为 V2.0（尽调启动引擎）
- 新增轮次差异化策略
- 新增清单发送策略

**V2.0（2026-04-03）**
- 基于历史实践反馈优化
- 完成 risk_report 最终模板

**V1.0**
- 基础工作流定义
