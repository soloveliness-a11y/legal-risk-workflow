---
name: industry-research
description: |
  行业研究能力 — 独立能力型Skill，可被Phase 1(dd-prep)/Phase 2(dd-check)/Phase 3(risk-report)按需调用。
  3路研究（IPO问询+监管框架+实操补强）+跨境评估+ESG条件触发+天使简化，检索渠道不限（搜索/行业媒体/社区均可）。
  触发词：行业研究、行业调研、industry-research、专项调研；旧称 industry_research
metadata:
  version: "2.0"
  bundle: "0.3.0"
  tags: "私募, 风控, 行业研究, 尽调, 能力型, 跨阶段"
---
# industry-research — 行业研究能力

## 定位

独立能力型Skill，不属于任何特定Phase。由 `risk-workflow` 编排器或父技能按需调用。

**核心输出：** 3路研究md + 单一 `sources_industry.json` + 条件触发的跨境/ESG专项报告

**契约引用：** [../risk-workflow/CONTRACT.md](../risk-workflow/CONTRACT.md) §7.4（检索与来源落盘）、AC3（来源标注）、AC5（降级显式化）、§7.2（OCR）、§4.2（子确认）、§2.3（确定性标签）。

**可选资源：** `{workspace}/knowledge-base/行业专项检查库/`（存在时，研究启动前加载对应行业的检查要点）。

---

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| industry | string | ✅ | 所属细分赛道 |
| output_dir | string | ✅ | 研究结果存放目录 |
| risk_hypotheses | string | ❌ | risk_hypotheses.md路径（优先级聚焦用） |
| crossborder_trigger | boolean | ❌ | 是否触发跨境评估 |
| esg_trigger | boolean | ❌ | 是否触发ESG评估 |
| investment_stage | string | ❌ | 投资轮次（天使简化研究范围） |

## 输出

| 产物 | 文件名 | 必选/条件 |
|------|--------|----------|
| IPO问询+同类风险 | `research_01_ipo_and_risks.md` | 必选 |
| 监管框架+政策 | `research_02_regulation.md` | 标准模式 |
| 实操补强 | `research_03_practice.md` | 标准模式 |
| 全部来源（单一文件） | `sources_industry.json` | 必选（§7.4 门禁） |
| 跨境评估 | `research_04_crossborder.md` | 条件触发 |

> 全部来源统一落盘为**单一** `sources_industry.json`，按 route 分组。

---

## 执行流程

```
输入参数解析
  → [子确认] 研究范围确认（含跨境自动检测）
  → 研究1（IPO问询+风险回溯）
  → 研究2（监管框架+政策趋势）
  → 研究3（实操补强：搜索+行业媒体+社区）
  → [条件] 跨境评估 → research_04_crossborder.md
  → [条件] ESG专项评估
  → 来源落盘门禁检查（sources_industry.json）
  → [子确认] 研究完成确认
  → 归档（普通目录）
  → 完成
```

### 确认点说明（CONTRACT §4.2，非阻断子确认）

| 确认点 | 位置 | 动作 |
|--------|------|------|
| 范围确认 | 研究启动前 | 展示行业匹配度+研究范围（标准/天使简化/跨境/ESG）+预计产出。**跨境自动检测**：如项目有境外子公司/境外收入/境外架构但调用方未传 crossborder_trigger → 主动提示审批人"检测到跨境特征，建议启用跨境评估" |
| 完成确认 | 全部研究完成 | 展示产出摘要（每路1-2句关键发现）+质量检查结果，审批人确认后下游可用。**硬验收（确认不能豁免）**：sources_industry.json 缺失或任一路 sources 为空 → 补齐前交付不成立（§7.4 / AC3） |

---

## 详细步骤

### 研究1: IPO问询焦点 + 同类风险回溯

- **检索意图：** 通用搜索（IPO问询函、被否案例、同行业尽调风险）
- **关键词：** `{industry} IPO问询` / `{industry} 被否` / `{industry} 尽调 风险`
- **重点关注：** 业务独立性、关联交易、客户集中度、IP权属、数据合规、出口管制
- **天使简化：** 仅查特许资质+前雇主IP/竞业风险
- **输出：** `research_01_ipo_and_risks.md`（来源并入 sources_industry.json route=01）

### 研究2: 行业监管框架 & 政策趋势

- **检索意图：** 通用搜索（监管框架、准入资质、政策变化）
- **关键词：** `{industry} 监管 框架` / `{industry} 准入 资质` / `{industry} 政策 变化`
- **整理：** 主管部门、法规体系、准入资质、近2年变化、特有合规义务
- **输出：** `research_02_regulation.md`（route=02）

### 研究3: 实操补强（通用检索，不绑定特定平台）

- **检索意图：** 搜索引擎 + 行业媒体深度文章 + 社区讨论，三渠道互补；C端业务加消费者社区
- **关键词：** `{行业} 法律风险` / `{行业} 合规` / `{行业} IPO`
- **时间范围：** 近2年
- **要点：** 行业媒体深度文章优先于泛搜索结果；社区讨论用于发现真实客诉与实操风险，引用前须交叉验证
- **输出：** `research_03_practice.md`（route=03）

### sources_industry.json 格式（单一文件，全路由）

```json
{
  "industry": "<细分赛道>",
  "query_date": "<ISO 日期>",
  "routes": [
    {
      "route": "01",
      "research_type": "IPO问询焦点+同类风险回溯",
      "search_keywords": ["<行业> IPO问询", "<行业> 被否"],
      "sources": [
        { "url": "https://...", "title": "文章标题", "source": "网页/行业媒体/社区",
          "search_keyword": "检索关键词", "retrieved_at": "<ISO 日期>" }
      ]
    },
    { "route": "02", "research_type": "行业监管框架+政策趋势", "sources": [] },
    { "route": "03", "research_type": "实操补强", "sources": [] }
  ],
  "archived_to": "<归档目录路径，归档后填>"
}
```

**落盘门禁（CONTRACT §7.4 / AC3）**：每路 sources 数组非空才可通过。公开检索确实无结果 → 该路标注 `📌待核实(公开检索无相关记录)` 并记录尝试过的关键词（AC5 显式化），不得静默留空。

---

## 异常与降级路径

| 场景 | 触发条件 | 处理动作 |
|------|---------|---------|
| 研究1/2 搜索无结果 | 检索返回空或无关 | 更换关键词重试1次；仍无 → 标注 `📌待核实(公开检索无相关记录)`，记录尝试过的关键词 |
| 研究3 渠道受限 | 某渠道超时/无结果 | 换其余渠道补足；全部失败 → 标注 `📌待核实(社区与行业媒体检索无结果)` |
| 遇扫描件 PDF | 有文本层则直接读 | 先试读，扫描件才 OCR（CONTRACT §7.2）；无 OCR 能力按 AC5 降级 |
| 行业名模糊 | 宽泛词（如"AI"、"新能源"） | 先与审批人确认细分赛道，不确定时取最相关子赛道 |
| 跨境/ESG触发不确定 | 边界条件模糊（如境外收入18%） | **倾向于触发（宁可多做不少做）**，但标注"条件边界" |
| 天使轮简化 | investment_stage="天使" | 研究1仅查特许资质+前雇主IP/竞业；研究2仅查准入资质；跳过研究3 |

---

## 条件触发：跨境项目境外法律评估

> **触发条件：** 境外实际经营子公司(非SPV) / 境外收入≥20% / 涉及境外架构

4项评估：

1. 外商投资审查（FDI/CFIUS）
2. 数据出境与隐私（GDPR/PIPL）
3. 行业准入限制
4. 制裁与出口管制（BIS/实体清单）

→ `research_04_crossborder.md`

---

## 条件触发：ESG专项评估

> **触发条件：** Pre-IPO / 境外收入≥20% / 新能源/环保/消费品/医药 / 有环保处罚线索

| 序号 | 检查项 | 适用 | 要点 |
|------|--------|------|------|
| E-1 | 环保合规与碳排放 | 全部 | 环评/危废/碳排放/EHS |
| E-2 | 供应链社会责任 | 制造业/消费品 | 供应商ESG/劳工/冲突矿物 |
| E-3 | 治理与商业道德 | Pre-IPO | 反腐/举报人/关联交易审批 |
| E-4 | ESG信息披露 | Pre-IPO | ESG报告/审核问询/评级 |
| E-5 | 数据隐私与AI伦理 | AI/大模型 | 隐私/算法公平性 |
| E-6 | 海外ESG合规 | 跨境 | EU CSRD/强迫劳动 |

ESG与跨境重叠→合并；ESG与数据合规重叠→E-5并入数据合规专项。

---

## 归档（普通目录）

研究完成后将 research_*.md + sources_industry.json 归档到跨项目复用的普通目录：

- 归档位置：`{workspace}/knowledge-base/research_archive/{行业}/`（不存在则创建）
- 归档后在 sources_industry.json 填 `archived_to` 字段
- 复用规则：同行业研究启动前先查归档目录，已有素材作为输入增量更新，不重复全量检索
- 归档失败不阻塞流程，`archived_to` 留空并在 project_log 记录原因

---

## 研究成果落盘规则（强制）

每份研究md必须包含：

1. **完整发现** — 不只是摘要，要可独立引用
2. **来源标注** — 每条发现标注来源URL
3. **项目风险预判** — 末尾"风险预判"小节，结合项目特征给出初步判断

---

## 跨Phase调用场景

| Phase | 调用方 | 模式 | 说明 |
|-------|-------|------|------|
| Phase 1 | dd-prep | 标准3路研究 | 首次行业研究 |
| Phase 2 | dd-check | 单路定向 | 核查中发现新行业问题 |
| Phase 3 | risk-report | 单路定向 | 报告撰写中需深入分析 |

---

## 风险假设聚焦（可选）

如传入 `risk_hypotheses` 路径：

1. 读取 risk_hypotheses.md
2. 高优先级假设对应的方向分配更多研究时间
3. 每个假设在研究中标注"验证方向"或"未覆盖"

---

## 质量检查

- [ ] research_01 已生成且非空
- [ ] sources_industry.json 已生成，route=01/02/03 各自 sources 非空（确实无结果的路已按 AC5 显式标注）
- [ ] 标准模式：research_02/03 已生成
- [ ] 条件触发：跨境/ESG 已评估（如适用）
- [ ] 来源标注完整（每条发现有来源URL）
- [ ] 每份 research_*.md 包含"风险预判"小节
- [ ] 归档已完成（archived_to 非空或已记录失败原因）
- [ ] 风险假设聚焦已应用（如有）

---

## 版本

当前版本以 frontmatter `version` 为准；完整版本历史见 [CHANGELOG.md](./CHANGELOG.md)。
