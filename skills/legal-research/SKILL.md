---
name: legal-research
description: |
  法源验证能力——验证法律命题有没有现行、适用、足够权威的依据。
  通过法源检索适配器（远答法规库/企查查法规库/手工核验）核验条文现行有效性，
  产出结构化 authority_record（含 proposition_id 供下游风险项引用）。
  被 dd-prep/risk-report/report-review/txn-docs 跨阶段调用。；旧称 legal_research
metadata:
  version: "1.0"
  bundle: "0.2.2"
  tags: "私募, 风控, 法源验证, 尽调, 能力型, 跨阶段"
---

# legal-research — 法源验证能力

> 本技能重心是**法源验证方法论**（法律命题 → 现行有效权威依据的 authority chain 构建）。
> 流程护栏（状态文件、验收契约、依赖降级）统一见 [CONTRACT](../risk-workflow/CONTRACT.md)，本文件不复述、只引用。

---

## 1. 定位与触发

**核心问题：验证一个法律命题有没有现行、适用、足够权威的依据。**

不是"查法条"——检索只是手段，交付物是 **authority chain**：报告中每个法律命题都能回溯到一条现行有效、文义实质匹配的权威依据；匹配不上就显式降级，不以沉默冒充有依据。

- 独立能力型 Skill，与 industry-research 平行：后者研究**行业**（监管格局/问询焦点/实操风险），本技能验证 **authority**（命题级法源核验）；行业研究中发现的监管命题要写进报告，仍须经本技能核验。
- 触发词：法条核验、法律依据、legal-research、authority check、条文有效性

**跨阶段被调用场景：**

| 调用方 | 场景 | 消费方式 |
|--------|------|---------|
| dd-prep | 行业监管框架成型 | 框架中要引用的监管命题先行核验 |
| risk-report | Ch.5 Rule 段法条引用 | 风险项挂 `legal_propositions: ["L003"]` 引用 |
| report-review | 法条时效审计 | authority audit：复查 effective_status 与 verified_at |
| txn-docs | 条款依据确认 | 交易条款援引的法源核验，防引用失效条文 |

---

## 2. 法源适配器（CONTRACT §7 模式）

| 适配器 | 检索方式 | 适用场景 | 凭证 |
|--------|---------|---------|------|
| 远答法规库 MCP | 语义检索 `law_vector_search` + 条文逐字 `ft_detail` | "这个情形适用什么法"（语义召回强） | API Key |
| 企查查法规库 MCP | 关键词 `get_legal_article_search` + 引用核验 `get_legal_citation_verify` | "这段文字里的法条还对不对"（逐字核验强） | 与 QCC CLI 同账户 |
| 手工核验模式（默认可用） | 国家法律法规数据库/人大网/国务院网/两高官网人工查证 | 零外部依赖兜底 | 无需凭证 |

**选择规则：**

1. 命题是自然语言情形描述（不知道适用哪部法）→ 远答语义检索先行
2. 命题已含具体法条引用或成段文本 → 企查查引用核验（`get_legal_citation_verify` 支持整段文本批量回库校验）
3. 两个 MCP 适配器均不可用 → 手工核验模式（核心链路零外部依赖可跑通，CONTRACT §7 原则）
4. 高风险命题（将支持高🔴/中高🟠 定级的依据）→ 双适配器交叉验证；结论冲突时以**条文逐字原文 + 官方数据库**为准

**适配器语义统一**：无论后端是什么，产出同一 authority_record schema（§3）；适配器差异只体现在 `source_ref` 与检索路径，不产出第二套格式。

---

## 3. authority_record Schema

```json
{
  "proposition_id": "L001",
  "proposition": "待验证的具体法律命题",
  "jurisdiction": "PRC",
  "authority_type": "statute | regulation | judicial_interpretation | exchange_rule | case | guidance | practice",
  "authority_name": "中华人民共和国公司法",
  "provision": "第265条",
  "issuer": "全国人大常委会",
  "effective_status": "effective | amended | repealed | superseded | uncertain",
  "effective_date": "2024-07-01",
  "verified_at": "2026-09-17",
  "source_ref": "远答法规库/企查查法规库/人工核验",
  "holding": "控股股东、实际控制人的定义",
  "limitations": "仅适用于2024-07-01后设立或发生的行为",
  "confidence": "high | medium | low"
}
```

**关键设计——proposition_id（L 编号）**：

- `L001`、`L002`…三位数字起编，项目内唯一、**跨版本稳定**：一旦写入 `legal_authority.json`，不得重排、不得复用；新增追加编号；合并命题保留较早编号（纪律同 CONTRACT §5 的 R 编号）
- 下游 risk-report 的风险项通过 `legal_propositions: ["L003", "L011"]` 字段引用，形成 **authority chain**：R 编号（风险）→ L 编号（法源）→ 条文逐字原文
- 孤儿引用（风险项引用了不存在的 L 编号）= AC4 类一致性问题，交付前必须消解

字段级填写规则、effective_status 判定标准与完整示例见 [references/authority_schema.md](./references/authority_schema.md)。

---

## 4. 五类法源分类表

| 类型 | authority_type | 使用边界 |
|------|---------------|---------|
| 法律/行政法规/司法解释 | statute / regulation / judicial_interpretation | 直接支持法律义务 |
| 监管规则 | exchange_rule | 支持监管要求（CSRC/HKEX/交易所规则） |
| 裁判/问询/监管函 | case / guidance | 支持解释和实务判断 |
| 内部风控经验 | practice | 仅用于风险筛查提示，**不得写成法律依据** |
| 历史模式 | practice | 仅用于校准，**不能作为 authority 引用** |

**红线**：practice 类 record 不得单独支持法律结论——报告写"实践中一般…"可以，写"依据…应当…"不行；历史模式只用于评级校准（report-review 同类对比），不进入 Rule 段。

---

## 5. 执行流程（Inputs → Checks → Outputs → Acceptance）

### Inputs

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| propositions | string[] | ✅ | 待验证命题：自然语言命题或含条文引用的文本段，一句一个命题 |
| project | string | ✅ | 项目名（定位/落盘 `legal_authority.json`） |
| jurisdiction | string | ❌ | 法域，默认 PRC；跨境项目标注具体辖区 |
| strictness | string | ❌ | `high`＝命题将支持高/中高风险定级，启用双适配器交叉验证 |

### Checks（四步，顺序执行）

1. **适配器检索**：按 §2 选择规则路由；语义命题走远答，条文引用/成段文本走企查查；零命中换关键词重试 1 次再换适配器
2. **现行有效性核验**：判定 effective_status；修订频繁的法特别核对版本与条号（如《反不正当竞争法》2025 修订后条文序号已变）
3. **条文逐字核验**：以 `ft_detail` / `get_legal_article_detail` 取逐字原文填入 holding；**禁止凭记忆默写条文**——记忆条号是法条引用幻觉的主源头
4. **实质匹配判定**：命题与条文在文义、适用范围、时间效力上实质对应才判匹配；仅主题相关（泛匹配）→ confidence 降为 medium 并在 limitations 说明差距

### Outputs

- `projects/{项目}/legal_authority.json`：authority_record 数组，追加式合并（同 proposition_id 更新字段并刷新 verified_at，不重复占位）
- **未核验项清单（AC5 显式化）**：uncertain 项 + 未核验原因 + 已尝试的适配器与检索词，随 record 一并落盘或在 project_log 登记

### Acceptance（交付即验收）

- [ ] 每条 record 的 `effective_status` 与 `verified_at` 非空
- [ ] `effective_status` 非 effective 的引用，在 record 与下游引用处均显式标注
- [ ] practice 类 record 未单独支持任何法律结论
- [ ] 未核验项清单存在；零命中项记录了已尝试路径
- [ ] `legal_authority.json` 内无重复 proposition_id；下游引用的 L 编号均可回溯（无孤儿引用）

---

## 6. 与 CONTRACT 的关系

| 契约条款 | 本技能适用说明 |
|---|---|
| §1 数据总线 | 产出落盘 `projects/{项目}/legal_authority.json`（项目级共享，与 Dossier 平级：dd-prep 核验过的法源，risk-report/report-review/txn-docs 直接引用，不重复核验） |
| §7 适配器语义 | 法源适配器实现"采集意图 → 结构化结果"：命题输入 → authority_record 输出 |
| §6 AC3（扩展） | 法条引用须有 authority_record 支撑——report-review authority audit 将无 record 支撑的法条引用退回 |
| §6 AC5 | 未核验命题显式列清单，不以沉默冒充无风险 |
| §5（类比） | L 编号纪律同 R 编号：跨版本稳定，不重排不复用 |
| §3 output.json | 最小 schema（skill=legal-research），随 legal_authority.json 同目录落盘 |
| §9 启动自检 | 每次执行前读 project_log 末尾，判断阶段与上次核验残留 |

**下游消费**：risk-report 风险项 `legal_propositions` 字段 / report-review authority audit / txn-docs 条款依据确认（详细衔接协议见 [references/authority_schema.md](./references/authority_schema.md) §5-§7）。

---

## 7. 降级（AC5）

| 场景 | 触发条件 | 处理动作 |
|------|---------|---------|
| 适配器不可用 | 无 API Key / MCP 未挂载 / 积分耗尽 | 切**手工核验模式**：国家法律法规数据库/人大网/国务院网/两高官网人工查证；record 标注 `source_ref: "manual"` + `verified_at`，并注明查证的官方网站 |
| 命题无法核验 | 双适配器 + 手工均零命中，或结果冲突无法裁决 | 标注 `effective_status: "uncertain"` + `confidence: "low"`，**不得作为法律结论依据**；下游只能写"依据某某法相关规定（待核）" |
| 检索零命中 | 关键词无结果 | 换关键词重试 1 次 → 换适配器 1 次 → 手工模式兜底 → 仍无按 uncertain 登记（记录尝试过的检索词） |
| 知识库 last_verified 过期 | 索引文件核验日期距今超过 90 天（默认阈值，可在 config 调整） | 引用前重新核验该法域，不直接沿用索引结论 |
| 修订敏感法 | 近期有修订记录的法（条号易变） | 以条文逐字原文核验为准，禁止沿用旧条号 |

---

## 8. 资源索引

| 资源 | 路径 | 用途 |
|------|------|------|
| 法律法规索引 | `knowledge-base/法律法规索引/` | 场景→条款 issue map（公司法/证券法/数据合规 3 模块 + README）；文件头部核验日期即 last_verified，过期触发重验 |
| authority_record 详细定义 | [references/authority_schema.md](./references/authority_schema.md) | 字段级填写规则、effective_status 判定标准、完整示例、authority chain 校验 |
| 核心契约 | [../risk-workflow/CONTRACT.md](../risk-workflow/CONTRACT.md) | 流程护栏唯一定义 |

---

## 版本

当前版本以 frontmatter `version` 为准；完整版本历史见 [CHANGELOG.md](./CHANGELOG.md)。
