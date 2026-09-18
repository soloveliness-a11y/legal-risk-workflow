# AI Agent 风控工作流使用指南

> 版本：v0.3.0（与 [skills/risk-workflow/CONTRACT.md](../skills/risk-workflow/CONTRACT.md) 对应）。本指南描述系统的用法与边界；技能内部规则以各 SKILL.md 与 CONTRACT 为准，两者不一致时以 CONTRACT 为准。
> 本系统不构成法律意见。生成的尽调结论、风险评级、报告和交易文件均须由具备经验和权限的专业人员独立复核（见 [README 免责声明](../README.md)）。

## 1. 这是什么

一套面向 PE/VC 法律尽调与投后工作的 Agent 技能包。它把尽调准备、资料核查、访谈纪要、风险报告、报告复核、交易文件审查和投后跟踪拆成可组合的技能，用共享的数据结构（Dossier、证据登记、风险编号）和交付验收（AC1-AC5）连接起来。

三个设计决定值得先知道：

1. **主干固定，分支有限**。工作流主干是 6 个阶段；尽调启动、报告定稿、交易与投后基线三个人工审批检查点必须由人放行，Agent 不能替审批人作最终风险判断。它可以在明确的分支点建议补充调查、补材料或终止。尽调收口不再单独打断：默认随报告初稿一并审批，只在足以改变核心结论的缺口出现时停下等待决定。
2. **结果靠验收约束，不靠逐步监督**。每个技能交付前要过对应验收项（事实可回溯、跨文档一致、降级显式标注等），验收不过即交付不成立。
3. **外部依赖全部适配器化**。工商数据、OCR、第二信源、法源检索都是可插拔接口，缺什么都不阻断核心链路：没有适配器时走手工采集或人工核查，并在产出中标明限制。

## 2. 安装与首次运行

需要 macOS/Linux、Python 3.10+。三步：

```bash
git clone https://github.com/soloveliness-a11y/legal-risk-workflow.git
cd legal-risk-workflow
python3 -m pip install -r requirements/core.txt && bash scripts/first_run.sh
```

`first_run.sh` 会检查 Python 版本、依赖、脚本语法编译、核心 CLI 冒烟与技能规范校验；任一核心项失败会以非零退出。外部适配器（工商数据源 CLI、OCR、第二信源）都可以不配置，需要时按 [config.example.yaml](../config.example.yaml) 填写。

技能发现方式按宿主不同：

| 宿主 | 方式 |
| --- | --- |
| Claude Code | 将 skills/ 下目录复制到 ~/.claude/skills/ 或项目级技能目录 |
| Codex 等支持 .agents/skills 的环境 | 仓库根目录已内置 `.agents/skills` 符号链接，克隆后即可发现 |
| 其他 Agent | 保留 skills/、knowledge-base/、templates/、scripts/ 的相对关系，在宿主指令中声明仓库路径 |

注意：复制技能目录只用于发现；技能运行时依赖仓库根目录的 scripts/、templates/、knowledge-base/，完整仓库必须留在原位。技能正文中的 `{workspace}` 均指仓库根目录。

## 3. 触发方式与项目结构

对你的 Agent 说"启动新风控项目"（或使用 [commands/start-project.md](../commands/start-project.md)），把材料路径和要解决的决策问题告诉它即可开始——项目名、投资阶段等字段能从材料识别，识别不了才问一次；推断与缺省项在尽调启动检查点一并确认，不在启动时逐项询问。说"继续 {项目名}"可跨会话恢复；新材料到达走增量更新，只改受影响的判断并交付变更摘要。也可以单独触发任一能力技能（如"整理这份访谈转写稿"），不必走完整流程。

每个项目在仓库根目录的 `projects/{项目名}/` 下工作：

```
projects/{项目名}/
├── project_dossier.md      # 权威工作视图（§0-§15）
├── evidence_registry.json  # 证据链登记（claims + evidence）
├── project_log.md          # 项目日志（追加式，含检查点审批记录）
├── 01_dd_prep/             # 清单、访谈提纲、初筛卡、行业研究
├── 02_dd_check/            # 核查表、verification_table.json、pending_materials.json
├── 03_dd_interview/        # 纪要、综合归纳、interview_result.json
├── 04_risk_report/         # 报告 md、risk_matrix.json
├── 05_report_review/       # 复核意见、修改闭环记录
├── 06_txn_docs/            # 条款落实表、保全校验表、覆盖度报告
├── 07_post_invest/         # 法律台账、预警记录
└── research/               # 专项调研（可选）
```

文件系统就是数据总线：技能之间不传私有格式，只读写这些约定路径的文件。想快速看到完整走一遍的样子，可以用完全虚构的 [examples/synthetic-demo](../examples/synthetic-demo/)。

## 4. 工作流全景

### 6 阶段与检查点

| Phase | 名称 | 主技能 | 关键产出 | 主检查点 |
|---|---|---|---|---|
| 1 | 项目准备 | dd-prep（编排 qcc-scan / industry-research） | 尽调清单、访谈提纲、风险假设、初筛卡 | CP1 尽调启动确认 |
| 2 | 尽调执行 | dd-check、dd-interview、补充核查 | 核查表、纪要、pending 清单 | CP2 尽调收口（呈报，结论性缺口时阻断） |
| 3 | 报告撰写 | risk-report（步骤 5 调 legal-research） | 风控报告 + risk_matrix | 无（初稿交复核） |
| 4 | 复核 | report-review | 复核意见、修订闭环记录 | CP3 报告定稿确认 |
| 5 | 交易文件 | txn-docs | 条款落实表、保全校验表、覆盖度报告 | CP4 交易与投后基线确认 |
| 6 | 投后跟踪 | post-invest-check（qcc-scan 定期复查） | 法律台账、预警记录 | 持续运行 |

CP1/CP3/CP4 是阻断性的人工审批：未确认时技能停止等待，确认记录写入 project_log.md。CP2 是收口呈报：覆盖率与待核实清单随报告初稿一并交 CP3 审批，只有足以改变核心结论的缺口才单独阻断。技能内部的机械性确认默认合并进检查点呈报，不逐项打断。阶段允许回环（复核不通过可回 Phase 2 补调查或 Phase 3 改报告），回环时已有产物不覆盖、版本共存。

### 数据流转

一份数据沿链路单向供给：工商采集（qcc_cache.json）进入清单与初筛；核查表与纪要进入 Dossier 与证据登记；报告的 risk_matrix 带条款映射提示进入交易文件落实表；落实表进入投后台账。风险编号 R01+ 一经写入不得重排复用，编号贯穿报告、矩阵、落实表与台账（AC4 校验的对象）。

两条贯穿性的纪律：

- **确定性标签**。每条事实性字段带 value / source / certainty 等属性，六档标签（✅已确认、📌待核实、⚠️不一致、❌未提供、[BP声称]、[推断]）全库唯一定义。无 source 的数字与绝对性表述禁止出现在任何产出中。
- **证据链**。关键事实用 F 编号登记命题、E 编号登记证据，报告中的结论应能回溯到 evidence_registry。多来源冲突不静默选边，登记为冲突组后按裁决框架处理。

## 5. 技能速览

12 个技能的职责与触发场景。详细规则见各自 SKILL.md。

| 技能 | 职责 | 主要使用场景 |
|---|---|---|
| risk-workflow | 主编排器与契约持有者；读日志判阶段、管检查点 | 全流程入口 |
| dd-prep | 尽调准备：知识积累、风险假设、清单、访谈提纲 | 新项目启动 |
| qcc-scan | 工商数据采集规范（数据源无关，统一产 qcc_cache） | 各阶段取数、投后复查 |
| industry-research | 行业研究（IPO 问询、监管框架、实操补强三路） | Phase 1，或独立调研 |
| legal-research | 法源验证：核验条文的现行有效性与权威性 | 报告引用法条前 |
| dd-check | 资料核查：对照清单逐项核查、三触发点、增量模式 | 收到企业材料后 |
| dd-interview | 访谈纪要：零信息损耗改写 + 多场次归纳 | 拿到转写稿后 |
| risk-report | 风控报告撰写：IRAC 结构、五级评级、分章或整篇 | Phase 3 |
| report-review | 双层复核（AI 自查 + 整体风险判断复核）、版本管理 | 报告初稿后 |
| txn-docs | 风险到条款的映射审查、前轮权利保全 | 投决通过后 |
| post-invest-check | 投后台账 6 表、9 类预警、复合叠加升级 | 交割后持续 |
| workflow-retro | 工作流复盘：偏差诊断，防止流程频繁变更 | 项目复盘时 |

技能自 v0.2.0 起使用小写连字符命名（dd-prep、risk-report 等），旧下划线名称保留为描述中的检索别名。

## 6. 交付验收（AC1-AC5）

过程不逐点护航，靠五类硬验收约束结果：

| AC | 内容 | 适用 |
|---|---|---|
| AC1 零损失 | 人名/公司/数字/日期在改写产出中不静默丢失；纪要必有"关键信息与待确认事项"兜底板块 | dd-interview |
| AC2 覆盖度 | 矩阵与正文逐条对应；每个风险至少 1 条条款映射 | risk-report / txn-docs |
| AC3 来源标注 | 数字与绝对性表述可回溯到 source 与证据链，抽查不过整批退回 | 全部技能 |
| AC4 跨文档一致 | 风险编号、公司名、日期、金额在报告/矩阵/落实表/台账间一致 | 报告及下游 |
| AC5 降级显式化 | 依赖不可用时写明"本项未核查，原因"，禁止沉默冒充无风险 | 全部技能 |

报告类交付另有内容验收：重大风险判断（中🟡及以上）逐项过**五问**——发现了什么（已核实事实/公司陈述/推断分层）、依据是什么（可定位到材料、冲突不选边）、为什么重要（对交易/估值/履约/治理/退出的具体影响）、建议怎么办（下一步核实动作或交易条件）、什么新信息会改变判断。无项目事实支撑的通用提示填充正文、"未提供材料"写成违法违规、"未发现"写成"已排除"，任一出现即退回。

机械可判部分一条命令跑完：

```bash
python3 scripts/validate_delivery.py projects/{项目名}/
```

输出 PASS / WARN / FAIL，exit 1 表示有 FAIL。AC1 的实体比对与 AC3 的深度溯源仍需人工判断。

## 7. 可选适配器与数据边界

四类外部依赖全部默认关闭或可缺省，见 CONTRACT §7 与 [SECURITY_PRIVACY.md](../SECURITY_PRIVACY.md)：

- **工商数据源**：企查查 CLI 适配器或人工按公开渠道采集，同一 schema（qcc_cache.json）。缓存超过 7 天触发复查。
- **OCR**：扫描件先试读、后 OCR。合同、员工名册、财务报表、访谈材料、尽调报告、投资建议书等 S1 敏感材料默认禁止上传外部服务（本地 OCR 或人工转录）；已核验服务商保密义务且承诺不用于训练的，可配置 `paddleocr.s1_policy: trusted-provider` 后经逐次确认上传。
- **第二信源**：内部知识库类检索。URL 导入须显式确认（`--allow-external-send`）。
- **法源检索**：legal-research 的适配器接口；无适配器时人工查官方文本并按 AC3 标注，禁止凭模型记忆断言条号。

所有会外传数据的操作默认拒绝、显式确认后执行；TLS 校验默认开启。

## 8. 质量验证与边界

维护者用有限历史样本对重写后的系统做过回归测试，覆盖不同项目阶段和核心工作流环节；基准发现以覆盖为主、误报水平低，信息保真与契约执行机制均经真实执行检验。聚合口径与未充分验证项见 [EVALUATION.md](./EVALUATION.md)。

这些结果只说明该版本在有限样本上的测试情况，不代表一般准确率。投后检查、多场访谈综合和 CLI 适配器的真实运行覆盖仍然有限。首次使用建议先用自己的材料小规模对照验证。

知识库中的法律、监管与交易所数值按 [法律数字来源索引](../knowledge-base/法律数字来源索引.md) 登记来源；未登记来源的数值一律是检索锚点，项目执行时必须核验现行规则后才可写入结论。

## 9. 常见问题

**Q：不用外部数据源能跑吗？**
能。手工采集模式是默认路径：qcc-scan 定义"查什么、怎么结构化"，人工查询国家企业信用信息公示系统后填同一 schema。

**Q：报告必须是 docx 吗？**
md 先行，docx 是可选输出（`md_to_docx_enhanced.py`，依赖 python-docx）。无转换环境时 md 即最终交付物。

**Q：跨会话怎么恢复？**
说"继续 {项目名}"。编排器读 project_log.md 判断当前阶段，做一页启动自检后继续。

**Q：技能改了名，我的旧指令怎么办？**
v0.2.0 起技能名为小写连字符（如 dd-prep）。旧下划线名称保留为检索别名，通常仍能触发；建议更新为新名。

**Q：如何贡献或报告法律内容错误？**
见 [CONTRIBUTING.md](../CONTRIBUTING.md)，含法律内容纠错模板与隐私披露要求。

## 10. 参考文档

- [README.md](../README.md)：项目定位与快速开始
- [skills/risk-workflow/CONTRACT.md](../skills/risk-workflow/CONTRACT.md)：全部技能共享的唯一契约（数据总线、验收、检查点、适配器）
- [docs/EVALUATION.md](./EVALUATION.md)：回归测试聚合口径
- [docs/DESIGN_DECISIONS.md](./DESIGN_DECISIONS.md)：重构决策记录
- [docs/EXCLUSIONS.md](./EXCLUSIONS.md)：公开范围规则
- [docs/ROADMAP.md](./ROADMAP.md)：路线图与待办
- [SECURITY.md](../SECURITY.md) / [SECURITY_PRIVACY.md](../SECURITY_PRIVACY.md)：安全报告渠道与数据分级
- [scripts/README.md](../scripts/README.md)：脚本清单
