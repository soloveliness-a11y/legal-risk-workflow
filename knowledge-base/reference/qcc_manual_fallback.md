# 工商数据手工查询降级方案（qcc_manual_fallback）

> 手工查询流程适用于任何工商数据源缺失场景。

## 定位

与 [qcc-scan 技能](../../skills/qcc-scan/SKILL.md)的**手工采集模式**配套：当工商数据源 CLI / MCP 适配器不可用或失败时，按本指南逐项人工查询公开渠道，结果填入**统一 schema**（qcc_cache.json + findings_summary.json，`source: "manual"`），下游 dd-prep / dd-check / risk-report / post-invest-check 零改动。

## 调用前提

⚠️ **必须使用完整公司工商全称，简称会返回空或错配**
> 应使用「行政区划 + 字号 + 行业 + 组织形式」的完整全称（如「某某省某某智能科技有限公司」），而非品牌简称或曾用简称；仅有简称时须先验证全称，多结果匹配时交审批人确认。

## 手工查询渠道对照表

| 维度组 | 首选公开渠道（免费） | 备注 |
|--------|--------------------|------|
| 工商登记 / 股东 / 变更 / 分支 / 行政处罚 / 经营异常 / 年报 | 国家企业信用信息公示系统（gsxt.gov.cn） | 手工模式首选 |
| 诉讼立案 / 裁判文书 / 法院公告 | 中国裁判文书网、人民法院公告网 | 案号可交叉验证 |
| 失信 / 被执行 / 限高 | 中国执行信息公开网 | 自然人股东同样可查 |
| 专利 | 国家知识产权局专利检索系统 | 法律状态逐条核对 |
| 商标 | 中国商标网 | |
| 软件著作权 | 中国版权保护中心登记公告 | |
| 融资 / 舆情 / 招投标 / 备案 | 通用搜索 + 行业媒体 + 上市公司公告平台 | 非官方渠道，来源逐条落 query_log |

## 命令清单（有企查查 MCP / CLI 权限时的适配器路径）

CLI 语法：`qcc <分组> <工具> "<企业全称>"`；或经 mcporter 调用 MCP 工具。批量编排脚本存在时可用 `{workspace}/scripts/orchestrators/qcc_batch_scan.py`，不存在时逐条调用或转手工采集模式。

### 基础信息（6项）

```bash
mcporter call qcc-company.get_company_registration_info searchKey="{完整全称}"
mcporter call qcc-company.get_company_profile searchKey="{完整全称}"
mcporter call qcc-company.get_shareholder_info searchKey="{完整全称}"
mcporter call qcc-company.get_key_personnel searchKey="{完整全称}"
mcporter call qcc-company.get_change_records searchKey="{完整全称}"
mcporter call qcc-company.get_external_investments searchKey="{完整全称}"
```

### 风险信息（5项）

```bash
mcporter call qcc-risk.get_case_filing_info searchKey="{完整全称}"
mcporter call qcc-risk.get_judicial_documents searchKey="{完整全称}"
mcporter call qcc-risk.get_administrative_penalty searchKey="{完整全称}"
mcporter call qcc-risk.get_judgment_debtor_info searchKey="{完整全称}"
mcporter call qcc-risk.get_equity_pledge_info searchKey="{完整全称}"
```

### 知识产权（4项）

```bash
mcporter call qcc-ipr.get_patent_info searchKey="{完整全称}"
mcporter call qcc-ipr.get_software_copyright_info searchKey="{完整全称}"
mcporter call qcc-ipr.get_trademark_info searchKey="{完整全称}"
mcporter call qcc-ipr.get_internet_service_info searchKey="{完整全称}"
```

### 经营信息（3项）

```bash
mcporter call qcc-operation.get_financing_records searchKey="{完整全称}"
mcporter call qcc-operation.get_news_sentiment searchKey="{完整全称}"
mcporter call qcc-operation.get_bidding_info searchKey="{完整全称}"
```

## 交叉验证与数据处理要点（6项）

对采集数据按 qcc-scan 的 6 项风险信号规则处理（手工与自动模式一致）：

1. 股权结构图谱构建 → 识别代持/一致行动/境外实体（股东为自然人但与董监高名单不重叠 → 疑似代持）
2. 诉讼/仲裁/行政处罚统计 → 与公司材料（BP/投资建议书）声称逐项对照，差异标 ⚠️不一致，不自行判定哪方正确
3. 知识产权数量/类型统计 → 与公司材料声称对照（核心技术公司专利/软著过低或大量失效 → 权属疑点）
4. 融资历程时间线 → 识别特殊权利条款（优先清算/回购/反稀释）起算与到期点
5. 股权出质/冻结/限制 → 任何记录 severity 取最高档（关注高），逐条列明
6. 对外投资/分支机构 → 识别关联方，供 dd-check 交叉比对

**交叉验证纪律：** 案号在中国裁判文书网与人民法院公告网双源核对；工商信息以 gsxt.gov.cn 为准源；非官方渠道（融资/舆情）逐条落 query_log 并注明来源可信度。

## 统一 schema 填写纪律

- `source: "manual"` 必填；每条查询在 `query_log` 登记（渠道 + 日期 + 操作者），手工模式强制
- 抄录数字禁止约数化；查不到的维度填 `uncovered` 并写明具体原因，禁止以沉默冒充无风险（AC5 降级显式化）
- findings_summary 为数组，每项 5 字段齐全（category / item / severity / fact / source_ref）；severity 三档：关注高 / 关注中 / 关注低
- 增量复查场景：与已有 cache 比对，变更项标 [NEW]/[CHANGED]/[REMOVED]，产出 qcc_review_diff.json
