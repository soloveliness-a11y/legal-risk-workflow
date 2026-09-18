# 风控工作流核心契约（CONTRACT）

> 本文件是全部技能共同遵守的**唯一契约**，承载全部通用约束。
> 设计原则：**过程管控最小化，验收契约硬化，领域方法论零损失。**
> 各技能的 SKILL.md 只描述自己的专业逻辑与流程，凡与本契约重复的内容一律引用本文件、不再复述。

---

## 1. 项目工作区与数据总线

文件系统即数据总线。所有技能读写同一目录结构，跨技能衔接只通过约定路径的文件。

```
{workspace}/projects/{项目名}/
├── project_dossier.md          # canonical working view（见 §2）
├── evidence_registry.json      # 证据链登记（见 §2.5）
├── project_log.md              # 项目日志（追加式，见 §9）
├── 01_dd_prep/                 # 清单、访谈提纲、初筛卡、行业研究
├── 02_dd_check/                # 核查表、verification_table.json、pending_materials.json
├── 03_dd_interview/            # 纪要（模块A）、综合归纳（模块B）、interview_result.json、pending_items.json（访谈残留待核实项）
├── 04_risk_report/             # 分章或整篇报告、risk_matrix.json
├── 05_report_review/           # 复核意见、修改闭环记录
├── 06_txn_docs/                # 条款落实表、保全校验表、覆盖度报告、交易文件
├── 07_post_invest/             # 法律台账、预警记录
└── research/                   # 专项调研（可选）
```

**衔接字段**（消费方按此读取）：

| 产出方 | 文件 | 消费方 |
|--------|------|--------|
| dd-prep | `01_dd_prep/checklist_*.md/.json`、`risk_hypotheses.md`、`interview_outline.json` | dd-check / dd-interview / risk-report |
| qcc-scan | `qcc_cache.json` + `findings_summary.json`（schema 见 §7.1） | dd-prep / dd-check / risk-report / post-invest-check |
| dd-check | `verification_table.json`、`pending_materials.json` | risk-report |
| dd-interview | `interview_result.json`、`pending_items.json` | risk-report |
| risk-report | 报告 md + `risk_matrix.json`（含 `clause_mapping_hints`） | report-review / txn-docs / post-invest-check |
| txn-docs | 落实表 + 保全校验表 + 覆盖度报告 | post-invest-check |
| post-invest-check | 法律台账（6 表） | 投后周期复查 |

不使用任何技能间私有格式；JSON 文件是给人和脚本读的公共接口。

---

## 2. Dossier（canonical working view）

`project_dossier.md` 是项目全景档案、全流程的 **canonical working view（权威工作视图）**：报告生成与跨技能衔接的主读取入口。事实的最终依据是证据链（源文件 + evidence_registry），**Dossier 的可信度来自其可回溯性（§2.5），而非其自身**——"Dossier 正确"的意思是"其中关键事实能回溯到证据链"，不是"以 Dossier 记载为准"。**output 状态文件生成前，必须先完成 Dossier 更新。**

### 2.1 结构（§0-§15）

§0 元信息（项目名/阶段/轮次/当前状态）｜§1 公司概况｜§2 主体架构（股权/实控人/演变）｜§3 历史沿革｜§4 核心团队｜§5 知识产权｜§6 业务与经营｜§7 关联交易与独立性｜§8 财务与税务｜§9 合规与监管｜§10 诉讼与争议｜§11 融资历史与投资条款｜§12 关键风险信号｜§13 信息完备度矩阵｜§14 待办事项｜§15 信息来源索引

> 章节编号以 `templates/project_dossier_template.md` 为唯一权威定义。风险正式编号 R01+ 只出现在 §12 关键风险信号及下游产物中；dd-prep 阶段的早期信号用 S01/S02 前缀，避免与正式编号混淆。

### 2.2 字段属性（每条事实性字段 5 个必填属性）

`value`（值）/ `source`（来源，文件+位置或查询记录）/ `certainty`（确定性标签）/ `last_updated` / `updated_by`（技能名或"人工"）

### 2.3 确定性标签（全库唯一定义，禁止另造）

| 标签 | 语义 |
|------|------|
| ✅已确认 | 至少一个独立可靠来源核实 |
| 📌待核实 | 有信息但未核实，或来源单一 |
| ⚠️不一致 | 多来源冲突，需进一步核查 |
| ❌未提供 | 应提供而未提供 |
| [BP声称] | 仅来自公司自述材料（商业计划书/访谈） |
| [推断] | 由其他事实推理而来，必须写明推理链 |

**纪律**：无 `source` 的数字与绝对性表述禁止出现在任何产出中；`[推断]` 传导到下游时标签不得丢失或升级。

### 2.4 更新与冲突

每个技能执行结束前更新自己负责的章节 + §0 元信息 + §15 来源索引。遇到与现有内容冲突的事实：先标注 ⚠️不一致 并在 §12 登记，交由核查环节（dd-check 或补充尽调）裁决，不静默覆盖。

### 2.5 Evidence Registry（证据登记）

每个项目维护 `projects/{项目}/evidence_registry.json`，登记支撑关键事实的证据链。结构为 `claims`（命题定义）+ `evidence`（证据记录）两部分：

```json
{
  "claims": { "F012": "截至2026-08-31，A股东持股18.32%" },
  "evidence": [
    { "evidence_id": "E023", "claim_id": "F012", "source_ref": "股东名册.pdf",
      "locator": "p.7 表2", "source_type": "signed_agreement",
      "source_date": "2026-08-31", "certainty": "confirmed",
      "contradiction_group": "C003" }
  ]
}
```

**evidence 核心字段（7 个，contradiction_group 可选）**：
| 字段 | 说明 | 示例 |
|------|------|------|
| evidence_id | 证据编号 | E001 |
| claim_id | 所支撑的事实命题编号 | F012 |
| source_ref | 来源文件 | 股东名册.pdf |
| locator | 定位 | p.7 表2 / §3.2 |
| source_type | 来源类型 | signed_agreement / registry / interview / BP / media / audit |
| source_date | 文件形成日期 | 2026-08-31 |
| certainty | 确定性 | confirmed / claimed / inferred |
| contradiction_group | 冲突组（可选） | C003（同组证据存在矛盾） |

**claim 落点（防孤儿引用）**：`claim_id` 必须在 `claims` 映射中有命题文本定义。evidence 中出现未在 `claims` 定义的 claim_id，视为孤儿引用，按 AC3 抽查退回。

**登记职责**：dd-check 对每个关键已确认事实（✅）与每个冲突事实（⚠️）分配 F 编号并登记对应证据（F = 事实命题，E = 证据）；qcc-scan / dd-interview / risk-report 在产出新的关键事实或新证据时追加登记。F/E 编号一经分配不复用、不重排。

**三条不变量**：
1. 不得仅因来源"独立"就自动覆盖另一来源——冲突按 `knowledge-base/reference/evidence_resolution_framework.md` 裁决
2. 证据冲突必须显式登记（contradiction_group），不得静默选边
3. 冲突事实进入报告前必须形成 resolution 或保持 unresolved（⚠️ 标注）

Dossier 的定位是 canonical working view（见 §2）：其中关键事实应能追溯到 evidence_registry 中的证据链（evidence_id），确定性标签受证据链支撑。

---

## 3. 执行状态文件（output.json，最小 schema）

每个技能每次执行产出 `output.json`（放在本技能 Phase 目录下）：

```json
{
  "skill": "dd-check",
  "version": "<与 SKILL.md frontmatter version 一致，运行时填入，禁止手写死值>",
  "project": "<项目名>",
  "date": "<ISO 日期>",
  "status": "completed | partial | blocked",
  "outputs": ["<本技能本次产出的文件相对路径>"]
}
```

字段可按需追加扩展，但以上 6 项必填。状态文件的作用是跨会话状态锚点，**不作为阻断手段**——完整性靠 §6 验收契约保障。

---

## 4. 检查点体系

### 4.1 四个主检查点（人工审批，阻断性）

| CP | 位置 | 审批内容 | 通过后动作 |
|----|------|---------|-----------|
| **CP1 尽调启动确认** | Phase 1 末 | 风险假设清单 + 尽调清单 + 访谈提纲 | 进入现场尽调 |
| **CP2 尽调完成确认** | Phase 2 末 | 核查覆盖率 + 待核实清单 + 纪要完整性 | 进入报告撰写 |
| **CP3 报告定稿确认** | Phase 4 末 | 复核结论 + 修改闭环 | 报告封版，进入交易文件 |
| **CP4 交易与投后基线确认** | Phase 5 末 | 条款覆盖度 + 前轮权利保全 | 进入投后管理 |

- 主 CP 必须由**审批人**（用户或其指定的角色）明确确认后才可进入下一阶段；未确认时技能停止并等待。
- 确认记录写入 `project_log.md` 一行：`[CP{n}] {日期} {审批人} 通过/有条件通过 意见摘要`。不设签名模板。

### 4.2 子确认（可选，非阻断）

技能内部的重要中间判断（如风险假设成型、纪要单场完成、模式选择）建议向用户展示并获得口头确认，记一行日志即可。不设编号体系、不设签名。

---

## 5. 风险编号规则

- 每个风险 `R01`、`R02`…两位数字起编，跨版本稳定：**编号一旦写入报告，不得重排、不得复用**。
- 新增风险追加编号；合并风险时保留较早编号并在 risk_matrix 中注明合并关系。
- risk_matrix.json、报告正文、条款落实表、投后台账中的 risk_id 必须一致（见 AC4）。

---

## 6. 验收契约（硬验收——本体系的核心质量控制）

过程不再逐点护航；每个技能交付前跑对应的验收项，**验收不过 = 交付不成立**。

**统一验收工具**：`python3 scripts/validate_delivery.py projects/{项目名}/ [--phase {phase_dir}]`——机械可判部分（AC2 覆盖度/AC4 跨文档一致性/Schema 校验/AC5 绝对表述扫描）一条命令跑完，输出 PASS/WARN/FAIL。AC1 零损失比对和 AC3 深度溯源仍需人工判断。

| AC | 适用 | 验收内容 |
|----|------|---------|
| **AC1 零损失验收** | dd-interview | ① 关键实体全量比对：人名/公司名/数字/日期在产出纪要中出现情况与原始转写比对，不得静默丢失；② 兜底板块存在：「关键信息与待确认事项」章节必须存在且非空；③ 数字精确性：纪要中数字必须与原文一致，禁止约数化 |
| **AC2 覆盖度校验** | risk-report / txn-docs | 报告：risk_matrix 与正文逐条对应，无孤儿条目；交易文件：每个 risk_id ≥1 条条款映射，输出覆盖度报告 |
| **AC3 来源标注** | 全部技能 | 产出中所有数字与绝对性表述经 Dossier 的 source 字段回溯到源文件，关键事实进一步回溯 evidence_registry 证据链（§2.5）；抽查不通过即整批退回 |
| **AC4 跨文档一致性** | risk-report 及下游 | 风险编号、公司名、日期、金额在报告/矩阵/落实表/台账间一致；可用 `scripts/validate_delivery.py` 统一校验 |
| **AC5 降级显式化** | 全部技能 | 任何依赖不可用时（数据源/OCR/信源），产出中必须显式标注「本项未核查，原因：…」，禁止以沉默冒充无风险 |

---

## 7. 外部依赖适配器

所有外部依赖抽象为可插拔接口。**核心链路在零外部依赖下必须可跑通**（手工模式）。

### 7.1 工商数据源

**接口语义**：`采集意图 → 结构化结果`。无论自动查询还是人工采集，最终都填同一 schema：

```json
// qcc_cache.json（数据源无关）
{ "query_date": "<ISO>", "source": "qcc-cli | manual | <其他>",
  "basic_info": { "注册资本": "...", "实缴资本": "..." },   // risk_screener.py 读取的平铺字段
  "shareholders": { "actual_controller": { ... } },
  "risks": { "equity_quality": "...", "litigation": { "开庭公告": 0, ... }, ... },
  "items": { ...原始记录留档（可选）... } }

// findings_summary.json
[ { "category": "主体|股权|IP|诉讼|高管|…", "item": "<事项>", "severity": "关注高|关注中|关注低",
    "fact": "<事实描述>", "source_ref": "<指向 qcc_cache 或手工记录>" } ]
```

- `severity` 表示数据层面关注程度，**不是最终风险评级**（评级是 risk-report 的职责）。
- 实现：① 手工采集模式（默认可用）——按国家企业信用信息公示系统的公开维度人工查询填录；② 企查查 CLI 适配器（示例实现，有 API 权限者可选）。
- 新鲜度：缓存 >7 天需复查；复查可增量 diff，差异回填 Dossier 并触发标签复核。

### 7.2 OCR

原则：**先试读，扫描件才 OCR**。实现可插拔（PaddleOCR 或其他）。无 OCR 时按 AC5 降级显式化，列入 pending_materials。

数据边界（与 [SECURITY_PRIVACY.md](../../SECURITY_PRIVACY.md) 一致）：

- 敏感材料（合同/协议等交易文件、员工花名册、财务报表、资产与 IP 清单）**禁止上传外部 OCR 服务**：仅可用宿主本地 OCR 能力，否则人工转录关键页或按 AC5 降级标注。
- 非敏感第三方与公开材料（外部尽调报告、投资建议书、工商公示档案、访谈转写稿等）可经外部 OCR；调用脚本必须显式确认外传（`paddleocr_api.py --allow-external-upload`）。
- OCR 产物随源文件继承密级，存放与传播不得高于源文件允许的范围。

### 7.3 第二信源（可选）

内部知识库类依赖抽象为"第二信源"接口：输入问题，返回带来源的回答。缺失时直接跳过，不影响主流程。

### 7.4 检索与来源落盘

任何研究类产出（行业研究/专项调研）必须落盘 `sources_*.json`（URL + 标题 + 访问日期）。**无来源不通过**（AC3 的研究类形态）。检索渠道不限：通用搜索、行业媒体、社区讨论均可。

### 7.5 法源适配器（legal-research）

法条/法规类外部依赖抽象为"法源适配器"接口：输入 issue + 检索关键词（来自 `knowledge-base/法律法规索引/` 的 Issue Map），返回带条号、时效性、逐字原文的现行有效条文。

- 法律法规索引只做 issue spotting 与检索指引，**不硬编码条号**；条号与条文内容一律由本适配器在运行时获取。
- 产出中引用法律条文必须标注来源与时效性（现行有效/已被修订），与 AC3/AC4 衔接。
- 无适配器时手工查官方法源并按 AC3 标注来源；查不到现行版本时按 AC5 降级显式化，禁止凭训练记忆断言条号。

---

## 8. 文档产出

- **md 先行**：一切长文档先落 markdown 存档，再按需转 docx（转换是可选输出，不是流程环节）。
- Word 生成脚本与宿主路径解耦，通过 config 指定；无转换环境时 md 即最终交付物。
- 版本号规则：`V0.xd` 草稿迭代（x 递增），定稿 `V1.0d`；封版后修改走 `V1.xd`。

---

## 9. 项目日志与启动自检

`project_log.md` 追加式记录：每次会话开始追加一段（日期/技能/动作/结论/文件变更），**只追加不删改**。

**启动自检（任何技能开始执行前，一页）**：

1. 读 `project_log.md` 末尾 → 判断当前 Phase 与步骤
2. `project_dossier.md` 存在且 §0 状态与日志一致？不一致时先对齐（以日志+用户确认为准）
3. 本次执行需要的上游文件存在？（按 §1 衔接表）缺失时列清单问用户，不自行绕过
4. 上次执行是否有 blocked / 待办？有则先处理
5. 涉及主 CP 的，确认审批状态

---

## 10. 版本与兼容

- 每个技能在 frontmatter 维护自己的 `version`，正文禁止硬编码版本号字面量（一律"以 frontmatter 为准"）。
- CHANGELOG 记录变更；跨技能契约变更在本文件头部维护变更记录。
- 本契约由 `risk-workflow` 主调度器持有；其他技能以 `../risk-workflow/CONTRACT.md` 引用。

---

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-09-17 | Phase 1 Close-out：Dossier 语义统一为 canonical working view（§1/§2/AC3，"可信度来自可回溯性而非自身"）；§2.5 增加 claims 命题落点（防孤儿引用）与登记职责；证据/法源冲突一律经六维裁决，禁止任何"优先源自动获胜"规则 |
| 2026-09-17 | 新增 §2.5 Evidence Registry（evidence_registry.json 证据链登记 + 三条证据不变量，Dossier 定位调整为 canonical working view，裁决细则见 knowledge-base/reference/evidence_resolution_framework.md）；§7 新增 7.5 法源适配器（legal-research），法律索引去条号断言、条号由运行时获取 |
| 2026-09-15 | 契约化收敛：取代 _shared_specs S1-S16；16 检查点收敛为 4 主 CP + 可选子确认；output.json 压为最小 schema 并去除阻断语义；新增验收契约 AC1-AC5 与外部依赖适配器层 |
