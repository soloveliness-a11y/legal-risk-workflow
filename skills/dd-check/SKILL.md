---
name: dd-check
description: 尽调资料核查 — 对照尽调清单+工商数据源缓存+行业研究，逐项核查公司底稿资料，标注差异、遗漏和风险信号，输出核查表+待核实事项清单。支持三触发点（dd-prep轻扫描/清单回复核查/补充资料核查），全量+增量追加模式。触发词：资料核查、dd-check、尽调核查、底稿核查、交叉比对、补充核查（旧称 dd_check）
metadata:
  version: "4.2"
  bundle: "0.2.0"
  tags: "私募, 尽调, 资料核查, 交叉比对, 差异标注, 风险信号, 数据源对照, 增量追加, 三触发点"
---

# dd-check — 尽调资料核查

## 核心定位

**角色**：资深 PE/VC 尽职调查资料核查专家。
**铁律**：**交叉比对，不轻信单方材料。** 独立数据源（工商数据源适配器，如企查查；见 CONTRACT §7.1）与公司底稿不一致时，按 evidence_resolution_framework 六维度裁决（不自动选边），差异显式登记 contradiction_group（CONTRACT §2.5 evidence_registry），不得静默覆盖。

**文档互证降级模式**（独立数据源不可用时）：以底稿互为交叉源（协议 vs 数据包 vs BP vs 公司书面回复），来源标签用 `doc_cross_check`；无法互证的维度按 CONTRACT AC5 逐维显式声明「未核查」，禁止把未核查呈现为无风险。verification_table 增加顶层字段 `verification_mode: "standard" | "doc_cross_check"` 与 `overall_flag`（整体结论声明）。降级模式下 T2 的核心价值从"交叉验证与差异登记"转为"底稿内部一致性校验 + 缺口定位"，对公司自述类风险仍然有效。

## 契约引用

遵循 [`../risk-workflow/CONTRACT.md`](../risk-workflow/CONTRACT.md)（下称 CONTRACT），本文件不复述契约内容：

| 条款 | 本技能适用点 |
|------|-------------|
| §1 数据总线 | 产出落 `02_dd_check/`；消费 `01_dd_prep/` 清单、qcc_cache.json、research_*.md |
| §2 Dossier | 核查完成回填 §2-§10/§12-§15；冲突按 §2.4 标 ⚠️ 入 §12、按 §2.5 登记 evidence_registry（contradiction_group），不静默覆盖 |
| §3 output.json | 最小 schema + 扩展字段 `trigger` |
| §4 检查点 | 核查范围/结果摘要向用户展示确认（§4.2 子确认，记一行日志）；Phase 2 末 CP2 由主调度器把关 |
| §6 验收 | AC3 来源标注；AC5 降级显式化（数据源/OCR 缺失必须显式标注，禁止沉默） |
| §7 适配器 | §7.1 工商数据源；§7.2 OCR（先试读，扫描件才 OCR）；§7.3 第二信源（可选） |
| §9 启动自检 | 每次触发前执行一页自检 |

## 三触发点架构

资料核查贯穿尽调全过程，采用"一次性全量 + 增量追加"——每次新收到材料在已有核查表上追加，不重新执行全量核查。

| 触发点 | 时机 | 核查模式 | 核心产出 |
|--------|------|---------|---------|
| **T1 前期资料扫描** | dd-prep 期间 | 反向匹配：先有材料，判断覆盖哪些清单项 | available_materials.json（供 dd-prep 清单去重；由 dd-prep 代理执行，不独立调用本技能） |
| **T2 清单回复核查** | 公司按清单提供底稿 | 正向+反向匹配：清单→材料→逐项核查 | verification_table.json + pending_materials.json |
| **T3 补充资料核查** | 访谈后/报告过程中补充 | 增量核查：特定问题→针对性材料→验证 | verification_table.json 增量更新 + pending_materials.json 更新（+ delta 文件） |

**增量原则**：verification_table.json 持续累积（追加/更新，非覆盖）；pending_materials.json 动态更新（已核实移除、新发现追加）；三触发共享同一项目目录 02_dd_check/。

**触发条件**：
- T2：投资经理确认公司已提供尽调清单回复材料；必须同时使用正向+反向匹配
- T3：补充资料到手 / report-review 复核意见标注需补充 / 访谈发现新问题；增量项标注"新增T3"

## 上下游衔接

| 方向 | 技能 | 交互内容 |
|------|------|---------|
| 上游 ← | dd-prep | checklist（核查基准）、interview_outline（重点追问项） |
| 上游 ← | 工商数据源适配器 | qcc_cache.json + findings_summary.json（交叉比对源，CONTRACT §7.1） |
| 上游 ← | industry-research | research_*.md（行业风险） |
| 上游 → | dd-prep | T1：available_materials.json（避免重复索要已有资料） |
| 下游 → | dd-interview | pending_materials.json（访谈重点追问方向） |
| 下游 → | risk-report | verification_table.json + pending_materials.json |
| 回流 ← | report-review | 复核意见（待补充事项清单）触发 T3 |

## 启动

1. 执行 CONTRACT §9 一页启动自检（读日志定 Phase、核上游文件、先处理 blocked 待办）。
2. 与用户确认：项目名、触发类型（T1/T2/T3）、材料路径（支持 PDF/Word/图片/扫描件）、dd-prep 输出目录、清单路径（T2）、补充事项及来源（T3）。
3. 已有 02_dd_check/verification_table.json → 增量触发，读取后追加；无 → 首次触发，初始化核查表。

## 9 维交叉比对（权威定义）

> 「独立源」= 工商数据源适配器返回的结构化记录（CONTRACT §7.1），「底稿」= 公司提供的材料。T2/T3 时每维至少完成 1 项比对，不可选择性跳过。

| # | 维度 | 必查项 | 比对：独立源 vs 底稿 | 典型不一致 |
|---|------|--------|---------------------|-----------|
| 1 | 工商信息 | 注册资本/实缴资本/法定代表人 | 工商记录 vs 营业执照、章程 | 注册资本不一致 |
| 2 | 股权结构 | 全体股东名单及持股比例 | 工商记录 vs 股东名册 | 股东数量差异、代持未披露 |
| 3 | 对外投资 | 合并范围公司名单 | 工商记录 vs 公司说明 | 未披露子公司、体外循环 |
| 4 | 诉讼仲裁 | 重大诉讼列表 | 司法记录 vs 公司披露 | 遗漏重大诉讼 |
| 5 | 知识产权 | 专利/商标/软著数量与权属 | 登记记录 vs IP 清单 | 数量差异、权属纠纷 |
| 6 | 行政处罚 | 处罚记录 | 监管记录 vs 合规声明 | 未披露处罚 |
| 7 | 关联交易 | 关联方清单 | 穿透记录 vs 公司披露 | 遗漏关联方 |
| 8 | 经营异常 | 异常名录记录 | 监管记录 vs 合规声明 | 未披露经营异常 |
| 9 | 董监高画像 | 任职/兼职/对外投资/历史任职 | 高管穿透记录 vs 董监高名册与公司声明 | 遗漏兼职或关联、同业竞争、离职仍挂名 |

**第 9 维（董监高画像）比对要点**：
- 公司董监高名册 vs 高管任职与关联企业记录——是否遗漏兼职、关联企业
- 公司声称"无同业竞争" vs 高管控制企业/对外投资记录——是否实际控制或投资同业企业
- 创始人声明"已从前雇主离职" vs 历史任职记录——是否仍挂名
- 上游数据（qcc_cache 等）含高管字段时，必须纳入交叉比对

## 执行步骤

### 步骤1：材料收集与目录扫描

**1.1 读取上游**：checklist（T2 正向基准）、qcc_cache.json（交叉比对源）、research_*.md（行业风险）、interview_outline（重点追问）。

**1.2 扫描材料目录**（深度按触发点）：

| 触发点 | 扫描深度 | 动作 |
|--------|---------|------|
| T1 | 文件列表+抽查 | 列出文件名和类型，抽查 5-10 份关键文件，不做深度内容核查 |
| T2 | 全量扫描+深度核查 | 按类型分类（工商/证照/合同/财务/知产/劳动等）；扫描件按 CONTRACT §7.2 处理（合同/花名册/财务/清单类禁止外传 OCR，走本地/人工/AC5 降级），结果存 `{文件简称}_ocr.md` |
| T3 | 定向扫描 | 仅扫描本次补充材料，与已有核查表交叉定位 |

**1.3 材料分类**：按清单模块分类并标注状态——T1="已收到-待核查"；T2/T3 按 4 级标注；T3 补充项关联已有条目。

**1.4 T1 专项：输出 available_materials.json**（仅 T1）：

```json
{
  "project_name": "", "generation_date": "", "trigger": "T1",
  "available_materials": [
    { "module": "主体与股权", "item": "营业执照", "file_name": "营业执照.pdf",
      "file_path": "…", "brief_check": "抽查结论", "need_deep_check": false, "notes": "" }
  ],
  "summary": { "total_modules": 17, "modules_with_materials": 0, "modules_without_materials": 0 }
}
```

用途：dd-prep 读取后在清单中标注"已有资料勿重复要求"。T1 不产生 pending_materials.json（深度核查在 T2）。

### 步骤2：逐项核查（T1 跳过本步，T2 全量，T3 定向）

**2.1 材料完备性核查**：清单要求的材料是否已提供？是否完整？有无明显缺失？

清单回复口径核查：公司对清单项的答复分为六类——提供资料 / 不适用 / 无（注明"未取得"或"遗失"原因）/ 待查（注明预计时间）/ 叙述性书面说明 / 空白答复。空白答复指清单已发出但未获任何回复函（常见于历史案卷核查型 T2），整体按 ❌ 计并在核查表 verification_mode 旁声明"零回复场景"；笼统"无异常"一律按 ❌ 未提供处理。

**2.2 交叉比对核查（核心）**：按上文 9 维权威定义，每维至少完成 1 项"独立源 vs 底稿"比对。

**2.3 行业专项核查**：特定资质/牌照是否提供；行业特有合规义务（如算法备案、数据出境评估）；行业常见风险点是否充分回应。参考 `{workspace}/knowledge-base/行业专项检查库/`。

**2.4 前轮问题跟进核查**：前轮报告提出的问题，公司是否提供整改/回应材料，整改是否到位。

**2.5 第二信源交叉核查（可选，CONTRACT §7.3）**：对 ⚠️ 不一致项与高风险项，可向第二信源（如内部知识库）提问获取补充信息，与本地材料交叉比对；结果记入核查表来源字段。第二信源不可用时直接跳过，按 AC5 显式标注"未核查"，不影响主流程。

### 步骤3：差异标注与风险归类

**3.1 四级标注体系**（标签语义与 CONTRACT §2.3 一致，每项必须有具体说明）：

| 标注 | 含义 | 后续动作 |
|------|------|---------|
| ✅ 已提供+一致 | 材料齐备，与独立源一致 | 无需追问 |
| ⚠️ 已提供但不一致 | 有材料但与独立源/行业研究有差异 | 列入待核实（高优先） |
| ❌ 未提供 | 清单要求但未提供 | 列入待核实（按关键性分级） |
| 📌 需现场核实 | 只能访谈/现场确认 | 列入待核实（访谈重点）。📌 不与 ❌ 叠加计数：需现场事项统一入 pending_materials 的 on_site 板块承载 |

**3.2 风险大类归类**：主体与股权（注册资本/股东结构/实控人/质押冻结/代持）、业务与经营（资质许可/经营合规/商业模式）、资产与权属（知产/不动产/重大设备/资产独立性）、财务与税务（规范性/税务合规/关联定价）、劳动与社保（合同/社保公积金/核心人员竞业）、合规与监管（诉讼仲裁/行政处罚/数据合规/环保）、投资条款（对赌/回购/反稀释/优先权）。

**3.3 风险信号识别原则**：
- 未上市企业常见瑕疵（少量社保不足、租赁备案缺失）→ 降级"中低"，不夸大
- 重点关注：与独立源不一致、核心材料缺失、行业红线
- 区分"暂未提供"（时间问题）vs"无法提供"（实质风险）
- 尽调配合度本身是风险信号：资料提供的详实程度、单据内容能否满足实际商业需求、管理层配合度（含跟投场景下主导方是否给核查空间）不足时，配合度决定风险发现的天花板——"报告自认尚待完善"本身就是结论级发现，须在核查表标注并传导 risk-report；
- 以保密为由拒供基础资料（收入清单/银行流水/应收明细）的，投后治理缺陷概率高，标注为"范围受限"并以 signal_direction=↑ 传导（affected_report_section=前提说明），作定性提示而非仅罗列未获资料。

**3.4 风险信号传导标注**：对 ⚠️❌📌 项附加以下两字段，供 risk-report 判断影响程度：

| 字段 | 说明 |
|------|------|
| `signal_direction` | ↑增强（新发现负面）/ →稳定（确认无变化）/ ↓缓解（风险收窄） |
| `affected_report_section` | 影响的报告章节，如 §3.3 某子公司独立性 |

建议动作与置信度不设字段，由下游按上下文自行推断。

### 步骤4：输出

**4.1 verification_table.json**（增量追加：T1 初始化 → T2 全量 → T3 追加/更新）

```json
{
  "project_name": "", "check_date": "", "last_trigger": "T2",
  "trigger_history": [ { "trigger": "T2", "date": "", "materials_count": 0 } ],
  "summary": { "total_items": 0, "provided_consistent": 0, "provided_inconsistent": 0,
               "not_provided": 0, "need_on_site": 0 },
  "items": [
    {
      "module": "主体与股权", "checklist_item": "营业执照",
      "status": "已提供+一致",
      "company_data": "公司底稿记载", "source_data": "独立源记载", "difference": null,
      "risk_level": "低",
      "provided_at_trigger": "T2", "deep_checked_at_trigger": "T2",
      "verification_sources": ["qcc_cross_check", "second_source", "local_material"],
      "signal_direction": null, "affected_report_section": null,
      "notes": ""
    }
  ]
}
```

> `provided_at_trigger`=材料首次收到时机；`deep_checked_at_trigger`=深度核查完成时机（T1 时为 null，待 T2）。9 维覆盖情况按本文权威定义自查，不在 output.json 中自报字段。

**4.2 pending_materials.json**（待核实事项与待补资料清单；CONTRACT §1 衔接文件）

仅含 ⚠️+❌+📌 项，按优先级排序；T3 后已核实项移除，新发现追加。每条必须含：① 具体差异描述（数据A vs 数据B）② 数据来源标注（独立源 vs 公司材料）③ 至少 2 个建议访谈问题。

```json
{
  "project_name": "", "generation_date": "", "last_updated_date": "", "last_trigger": "T2",
  "total_pending": 0, "resolved_count": 0,
  "priority_high": [
    {
      "module": "主体与股权", "item": "股东名册差异", "status": "已提供但不一致",
      "detail": "公司提供5名股东 vs 独立源显示7名",
      "suggested_interview_questions": ["…", "…"],
      "source": "工商登记 vs 公司股东名册",
      "discovered_at_trigger": "T2", "resolved_at_trigger": null
    }
  ],
  "priority_medium": [], "priority_low": [], "on_site_verification": []
}
```

**问题质量标准**：❌"请确认股权结构"（太泛）；✅"股东名册显示 5 名股东，独立源显示 7 名，请确认是否存在代持或持股平台未披露"（具体+有数据支撑）。

**4.3 output.json**：CONTRACT §3 最小 schema（skill/version/project/date/status/outputs），扩展字段 `trigger`。

**保存路径**：`{workspace}/projects/{项目名}/02_dd_check/`。verification_table.json 与 pending_materials.json 每次触发后整体保存（含全部历史+本次增量）；T3 额外输出 delta 文件供 risk-report 快速定位。

### pending_materials.json 管道（跨技能）

- **T2**：建立全量待核实清单
- **T3 核查完成后（必做收尾）**：已核实项移除或标记 `resolved_at_trigger`；仍不充分的标注"部分补齐"+缺口；新发现需求追加
- **消费方**：dd-interview 读取聚焦追问并回写 interview_result；risk-report 读取判断信息缺口
- 旧项目如存在 `04_risk_report/pending_materials.json`（历史版本由 risk-report 产出），T3 后同步更新该文件保持一致

## T3 终止条件

T3 可多次触发，退出判断：
- pending_materials.json 为空 → 自动终止，展示核查完成摘要，可进入 risk-report
- 连续 2 次 T3 无新发现 → 建议终止，用户确认后标注 `termination_reason`
- 待补资料全部已补齐 → 自动终止，建议报告 V0.xd → V1.0
- 用户主动终止 → 标注 `termination_reason: "用户确认终止"`

## 更新 Dossier（CONTRACT §2）

核查完成后回填（Dossier 未初始化时先从模板创建并标注"dd-prep 未初始化"）：
1. §2-§10 各章节：✅项填入并标"已确认"；⚠️项标注差异和来源；❌项保持"待补充"；📌项进 §12
2. §12 关键风险信号：从 ⚠️❌📌 项提取，新增风险行（编号/事项/等级/状态:待确认/来源:dd-check/日期）
3. §13 信息完备度矩阵：已提供→🟢；仍有缺口→保持并更新描述
4. §14 待办事项：与 pending_materials.json 严格一致
5. §15 来源索引：记录本次新审阅文件；§0 元信息更新

填充原则：只更新有新信息的章节，不覆盖已确认信息；与既有事实冲突按 CONTRACT §2.4 标 ⚠️ 入 §12、按 §2.5 登记 contradiction_group 并按 evidence_resolution_framework 裁决，不静默覆盖。

## 质量自检（交付前）

- [ ] 触发点类型已识别；已有核查表为增量追加（非覆盖）；trigger_history 已更新
- [ ] T2/T3：9 维交叉比对每维至少 1 项；清单每项有 4 级标注结论；⚠️项有具体差异描述；❌项有关键性分级
- [ ] T1：available_materials.json 已生成；抽查文件无与独立源明显冲突；"已收到-待核查"标注正确
- [ ] 建议访谈问题具体可问（数据 A vs 数据 B）
- [ ] T3：补充项已更新状态；已解决项已移除；delta 已生成；pending_materials.json 已同步
- [ ] 关键 ✅ 事实与 ⚠️ 冲突事实已按 CONTRACT §2.5 登记 F/E 编号（`evidence_registry.json` 的 claims + evidence，claim_id 均有命题定义）
- [ ] 所有数字与绝对性表述有 source（AC3）；数据源/OCR 缺失项已显式标注（AC5）
- [ ] Dossier 已回填，§14 与 pending_materials.json 一致

## 异常与边界处理

| 场景 | 处理 |
|------|------|
| 材料不全（关键项缺失>30%） | 标注 `⚠️资料不足`，列出缺失项；推进核查但结果标"有条件" |
| 独立源与公司材料矛盾 | 登记 contradiction_group，按 evidence_resolution_framework 六维度裁决；未裁决前标 `⚠️矛盾：独立源 vs 公司材料`，双源并列不选边 |
| 行业研究无覆盖 | 标注 `[新风险模式]`，建议后续知识库更新 |
| OCR 失败 | 标注 `⚠️需人工核验（OCR失败）`，记录页码范围，列入 pending_materials |
| T3 与 T2 结论矛盾 | 新证据触发**重新裁决**（六维框架），不是 T3 自动获胜：如新结论仅因事实时点变化（事实本身更新），T2 旧结论标"已更新"并列示变更轨迹；如新旧证据对同一时点事实冲突，登记 contradiction_group、双源并列不选边 |
| T3 结论反复翻转 | 同一核查项结论连续翻转 ≥2 次时，列出翻转历史请用户确认后再继续，防止结论震荡 |

## 资源索引

| 资源 | 路径 | 用途 |
|------|------|------|
| 交叉比对维度 | 本文件"9 维交叉比对"节 | 权威定义 |
| 行业专项检查库 | `{workspace}/knowledge-base/行业专项检查库/` | 行业特有核查要点 |
| OCR | CONTRACT §7.2 | 底稿扫描件识别（先试读，扫描件才 OCR） |
| 核心契约 | `../risk-workflow/CONTRACT.md` | §1/§2/§3/§4/§6/§7/§9 |

## 版本

当前版本以 frontmatter `version` 为准；完整变更记录见 [CHANGELOG.md](./CHANGELOG.md)。
