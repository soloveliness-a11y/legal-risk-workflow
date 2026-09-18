# authority_record 结构定义

> legal-research 产出的结构化法源记录。字段级填写规则与示例在**产出时**读取；
> 下游（risk-report 挂 `legal_propositions` / report-review 做 authority audit / txn-docs 条款依据确认）消费时读取 §5-§7。

---

## 1. 完整 Schema（14 字段）

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
  "source_ref": "yuandian-law | qcc-legal-regulation | manual",
  "holding": "控股股东、实际控制人的定义",
  "limitations": "仅适用于2024-07-01后设立或发生的行为",
  "confidence": "high | medium | low"
}
```

---

## 2. 字段说明

| 字段 | 类型 | 必填 | 填写规则 |
|------|------|------|---------|
| proposition_id | string | ✅ | `L`+三位数字（L001…），项目内递增、跨版本稳定；一旦写入不得重排、不得复用；新增追加编号；合并命题保留较早编号（纪律同 CONTRACT §5 R 编号） |
| proposition | string | ✅ | 命题原文，**一句一个命题**；必须具体到可判定（如"新法下未实缴出资的股东对公司债务承担补充责任"），不接受主题词（如"出资问题"） |
| jurisdiction | string | ✅ | 法域代码，默认 `PRC`；跨境项目标注具体辖区（见 industry-research 跨境评估的 4 项范围） |
| authority_type | enum | ✅ | `statute` 法律 / `regulation` 行政法规 / `judicial_interpretation` 司法解释 / `exchange_rule` 监管规则（CSRC/HKEX/交易所）/ `case` 裁判文书 / `guidance` 问询函·监管函 / `practice` 内部经验与历史模式 |
| authority_name | string | ✅ | 法规全称**含版本年份**（如"中华人民共和国公司法(2023修订)"），避免同名不同版；case 类填案号对应文书标题 |
| provision | string | ✅ | 条号（"第265条"）；跨条引用给起止条号；case 类填案号；guidance 类填函件编号 |
| issuer | string | ✅ | 发布机关（全国人大常委会/国务院/最高人民法院/国家市场监督管理总局/交易所等），用于效力级别判断 |
| effective_status | enum | ✅ | 见 §3 判定标准 |
| effective_date | string | ✅ | 施行日期（ISO 格式）；case 类填裁判日期；用于时间效力判断 |
| verified_at | string | ✅ | 本次核验日期（ISO 格式）；超过 90 天被下游引用时触发重验 |
| source_ref | string | ✅ | 适配器标识：`yuandian-law` / `qcc-legal-regulation` / `manual`；manual 须在 limitations 或 project_log 注明查证的官方网站名称 |
| holding | string | ✅ | 条文规范内容摘录或裁判要旨/监管口径（case/guidance 类尤其必填）；**必须来自逐字原文核验，不得凭记忆默写** |
| limitations | string | ❌ | 适用限制：时间效力（新旧法衔接）/ 适用范围（主体、行为类型、行业）/ 地域；无限制留空 |
| confidence | enum | ✅ | `high`＝逐字原文核验 + 实质匹配；`medium`＝单适配器命中或泛匹配（仅主题相关）；`low`＝uncertain / 传闻 / 推断 |

---

## 3. effective_status 判定标准与下游处理

| 状态 | 判定条件 | 下游处理 |
|------|---------|---------|
| effective | 法规库显示现行有效 + 条文逐字核验一致 | 可直接支持法律结论 |
| amended | 所引版本已被修订（条号可能漂移） | 引用处标注"已修订"；改引现行版本并**新开 L 编号**，旧编号保留映射关系 |
| repealed | 已废止（如《合同法》随民法典施行废止） | 禁止引用；命题仍可能成立的，重新检索现行依据 |
| superseded | 被新规或上位法取代 | 同 repealed，record 中注明取代关系 |
| uncertain | 无法核验 / 双源结果冲突无法裁决 | **不得作为法律结论依据**；报告只能写"依据某某法相关规定（待核）" |

---

## 4. authority_type 使用边界（五类法源）

| 类型 | authority_type | 使用边界 | 典型形态 |
|------|---------------|---------|---------|
| 法律/行政法规/司法解释 | statute / regulation / judicial_interpretation | 直接支持法律义务 | 公司法、证券法、司法解释 |
| 监管规则 | exchange_rule | 支持监管要求 | 交易所审核问答、上市规则、CSRC/HKEX 规则 |
| 裁判/问询/监管函 | case / guidance | 支持解释和实务判断 | 裁判文书、IPO 问询函、监管函 |
| 内部风控经验 | practice | 仅用于风险筛查提示，**不得写成法律依据** | 某类瑕疵的历史处理惯例 |
| 历史模式 | practice | 仅用于校准，**不能作为 authority 引用** | 同类项目风险评级惯例 |

**红线**：practice 类 record 不得单独支持法律结论——报告写"实践中一般…"可以，写"依据…应当…"不行；历史模式只用于评级校准（report-review 同类对比），不进入 IRAC 的 Rule 段。

---

## 5. proposition_id 与 authority chain

- **编号规则**：L001 起三位数字，项目内唯一；纪律同 R 编号（不重排、不复用、追加、合并保留较早编号）。
- **下游引用**：risk-report 的 `risk_matrix.json` 风险项追加字段：

```json
{ "risk_id": "R03", "risk_title": "…", "severity": "中🟡",
  "legal_propositions": ["L003", "L011"], "clause_mapping_hints": { … } }
```

- **authority chain 路径**：R 编号（风险）→ L 编号（法源命题）→ 条文逐字原文（holding）。
- **chain 校验规则**（report-review authority audit 执行，机械可判部分可脚本化）：
  1. 风险项引用的每个 L 编号在 `legal_authority.json` 中存在（无孤儿引用）
  2. 被引用 record 的 `effective_status = effective`；非 effective 的引用在报告正文显式标注
  3. 报告 Rule 段出现的法条均有对应 record 支撑（AC3 扩展：法条引用可回溯）
  4. `legal_authority.json` 内无重复 proposition_id

---

## 6. 完整示例

### 6.1 statute / effective / high（标准形态）

```json
{
  "proposition_id": "L001",
  "proposition": "控股股东、实际控制人滥用股东权利损害公司或其他股东利益的，应对损失承担赔偿责任",
  "jurisdiction": "PRC",
  "authority_type": "statute",
  "authority_name": "中华人民共和国公司法(2023修订)",
  "provision": "第21条、第265条",
  "issuer": "全国人大常委会",
  "effective_status": "effective",
  "effective_date": "2024-07-01",
  "verified_at": "2026-09-17",
  "source_ref": "yuandian-law",
  "holding": "第265条界定控股股东与实际控制人定义；第21条确立滥用股东权利的赔偿责任",
  "limitations": "2023修订版自2024-07-01施行；施行前发生的行为按时间效力衔接规定处理",
  "confidence": "high"
}
```

### 6.2 repealed / high（废止条文拦截）

```json
{
  "proposition_id": "L004",
  "proposition": "合同无效情形的法定列举",
  "jurisdiction": "PRC",
  "authority_type": "statute",
  "authority_name": "中华人民共和国合同法",
  "provision": "第52条",
  "issuer": "全国人大常委会",
  "effective_status": "repealed",
  "effective_date": "1999-10-01",
  "verified_at": "2026-09-17",
  "source_ref": "qcc-legal-regulation",
  "holding": "原五项合同无效情形；民法典施行时合同法同步废止，对应规则并入民法典合同编",
  "limitations": "禁止引用；报告须改引民法典对应条文并新开 L 编号",
  "confidence": "high"
}
```

下游处理：任何报告引用《合同法》第52条 → authority audit 直接退回。

### 6.3 amended / medium（条号漂移）

```json
{
  "proposition_id": "L007",
  "proposition": "混淆行为的认定标准",
  "jurisdiction": "PRC",
  "authority_type": "statute",
  "authority_name": "中华人民共和国反不正当竞争法(2019修正)",
  "provision": "第6条",
  "issuer": "全国人大常委会",
  "effective_status": "amended",
  "effective_date": "2019-04-23",
  "verified_at": "2026-09-17",
  "source_ref": "qcc-legal-regulation",
  "holding": "禁止实施引人误认为是他人商品或与他人存在特定联系的混淆行为",
  "limitations": "2025修订后条文序号已变；引用前须按现行版本重新核验条号",
  "confidence": "medium"
}
```

下游处理：单适配器命中 + 版本存疑 → confidence=medium，report-review 复核时强制重验。

### 6.4 uncertain / low（无法核验的传闻口径）

```json
{
  "proposition_id": "L011",
  "proposition": "某类架构须在监管窗口期内完成整改（未经成文规定确认的窗口指导传闻）",
  "jurisdiction": "PRC",
  "authority_type": "guidance",
  "authority_name": "（未能定位成文文件）",
  "provision": "",
  "issuer": "（未能定位）",
  "effective_status": "uncertain",
  "effective_date": "",
  "verified_at": "2026-09-17",
  "source_ref": "manual",
  "holding": "双适配器与官方网站检索均未找到成文依据",
  "limitations": "不得作为法律结论依据；报告只能写'据市场流传口径（待核）'",
  "confidence": "low"
}
```

### 6.5 practice（禁止作为法律依据）

```json
{
  "proposition_id": "L015",
  "proposition": "同类代持风险在 Pre-A 轮项目通常评为中🟡",
  "jurisdiction": "PRC",
  "authority_type": "practice",
  "authority_name": "内部风控经验（历史项目评级模式）",
  "provision": "",
  "issuer": "内部",
  "effective_status": "effective",
  "effective_date": "",
  "verified_at": "2026-09-17",
  "source_ref": "manual",
  "holding": "历史同类项目评级分布",
  "limitations": "仅用于评级校准与筛查提示；不得写入 Rule 段、不得表述为'依据…应当…'",
  "confidence": "medium"
}
```

---

## 7. 落盘与合并规则

- **文件**：`projects/{项目}/legal_authority.json`，顶层结构：

```json
{
  "project": "<项目名>",
  "updated_at": "<ISO 日期>",
  "records": [ { "…": "authority_record" } ]
}
```

- **追加式合并**：重复执行时按 proposition_id 合并——同 id 更新字段并刷新 `verified_at`，不重复占位；新命题追加新编号。
- **留痕**：每次核验后在 `project_log.md` 追加一行（本次核验数 / 新增 L 数 / uncertain 数）。
- **新鲜度**：record 的 `verified_at` 距今超过 90 天（默认阈值）被下游引用时，先重验再引用。
