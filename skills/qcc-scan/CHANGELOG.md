# qcc_scan 版本更新记录

> 完整版本历史记录。优化Skill或回溯变更时读取此文件。

## 版本记录

**V2.0（2026-09-15）— 开源重构：数据源无关采集规范**
- 定位从"企查查扫描能力"重构为"尽调数据采集规范（数据源无关）"：采集意图与执行者解耦，人工与自动采集填同一 schema，下游 diff/复查/消费零改动
- 新增手工采集模式（默认可用，重点建设）：公开渠道对照表（首选国家企业信用信息公示系统）+ 股权结构维度人工查询操作示例 + 手工纪律（query_log 查询记录 / uncovered 显式登记 / 数字禁约数化）
- 三梯队工具清单改写为维度清单：必查维度（11项语义不变）/ 按需维度 / 高管画像维度；董监高画像触发条件逻辑原样保留，不再绑定工具编号
- 6 项风险信号解读规则核心资产保留，并补充解读要点（代持/一致行动/特殊权利到期/关联方）
- 产出 schema 对齐 CONTRACT §7.1：findings_summary 字段改为 category/item/severity/fact/source_ref，severity 三档（关注高/中/低）且明确 ≠ 最终评级；qcc_cache 新增 source / query_log / uncovered 字段（AC5）；findings_summary 改为独立文件
- 企查查 CLI 降级为可选示例适配器：保留调用意图（单参数/双参数）与缓存/diff/复查逻辑（>7天复查、增量 diff、Dossier 回填）
- 删除：本机 PATH 硬编码、MCP→CLI 迁移叙事、E1-E42 工具编号清单、历史 key 映射表（含真实项目名，脱敏删除）、S2/S8 共享规范引用（改为 CONTRACT 引用）
- 检查点0/7 改为 CONTRACT §4.2 子确认（非阻断）；人名脱敏为"审批人"

**V1.3（2026-05-04）— 控制论复盘优化（schema标准化）**
- qcc_cache.json 标准 schema 新增 `schema_version: "1.3"` 字段（P0）
- findings_summary 格式强制校验：必须为数组、每项含4个必填字段、source_tool 使用 CLI 格式（P0）
- 新增 Step 5.5 格式校验子步骤（findings_summary 生成后必做）
- executives 调用条件从"按需"改为"条件触发"（竞业/IP/利益冲突假设→必调 E1-E6）（P1）
- qcc_cache_manager.py 新增 `validate` 子命令，校验 schema 合规性（P1）
- 新增附录：历史 key 映射表 + Python 适配代码示例（P2）
- 质量检查新增3项：schema_version / findings_summary数组格式 / source_tool CLI格式

**V1.0（2026-04-28）— 从dd_prep拆出，独立能力型Skill**
- 从dd_prep V3.1 步骤2（企查查预扫描）拆出
- QCC MCP工具列表引用S2（dd_prep法律尽调场景覆盖保留：IP/诉讼工具升级为必调）
- qcc_batch_scan编排器调用流程保留
- 6项数据处理规则独立化
- 新增增量更新模式（支持Phase 6投后对比：NEW/CHANGED/REMOVED标注）
- 新增跨Phase调用场景表（Phase 1/2/3/6）
- qcc_cache.json结构保持不变，向后兼容
- findings_summary结构保持不变，下游Skill无需修改

**核心价值：将企查查扫描从dd_prep绑定能力变为跨阶段独立能力，Phase 1(dd_prep)/Phase 2(dd_check交叉验证)/Phase 6(投后定期扫描)均可独立调用。**

**V1.2（2026-04-30）— 从 MCP 切换为 CLI 调用方式**
- 所有 QCC 调用从 MCP Server（5个/146工具）切换为 qcc-agent-cli（npm全局安装）
- MCP工具名格式 `qcc-company.xxx` → CLI格式 `qcc company xxx`
- 董监高双参数格式：`qcc executive xxx --searchKey "企业名" --personName "人名"`
- 单参数格式：`qcc {server} {tool} "企业名称"`
- PATH要求：Agent 宿主内置 Node（22.x）二进制目录
- mcp.json 中移除 5 个 qcc MCP Server，减少工具数量提升AI回复质量

**V1.1（2026-04-30）— 新增 qcc-executive 董监高画像**
- extended scope 新增第三梯队——董监高画像（42项工具）
- qcc_cache.json 输出结构新增 executives 字段（人员画像）
- findings_summary category 新增"董监高画像"
- 跨Phase调用场景新增 executive 相关行
- 董监高画像调用规则：需先获取 key_personnel 再逐人调用
