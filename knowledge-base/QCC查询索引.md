# 企查查常用查询字段说明

> 供 dd-prep/risk-report/post-invest-check Skill 参考企查查数据结构和常用查询路径。

## MCP 工具分类

| 服务 | 工具数 | 主要用途 |
|------|--------|---------|
| qcc-company | 12 | 工商基础、股东、高管、变更、对外投资、分支机构 |
| qcc-risk | 34 | 诉讼、立案、行政处罚、被执行、失信、股权出质 |
| qcc-ipr | 6 | 专利、软著、商标、ICP/APP/算法备案 |
| qcc-operation | 13 | 融资、新闻、招投标 |

## 推荐调用顺序

### 第一梯队（必调）
1. `qcc-company.get_company_registration_info` — 工商基础
2. `qcc-company.get_shareholder_info` — 股权结构
3. `qcc-company.get_change_records` — 历史变更
4. `qcc-ipr.get_patent_info` — 专利
5. `qcc-ipr.get_software_copyright_info` — 软著
6. `qcc-risk.get_lawsuit_info` — 诉讼
7. `qcc-risk.get_executed_info` — 被执行
8. `qcc-operation.get_financing_records` — 融资

### 第二梯队（按需）
- `qcc-company.get_key_personnel` — 高管
- `qcc-company.get_external_investments` — 对外投资
- `qcc-company.get_branches` — 分支机构
- `qcc-risk.get_administrative_penalty` — 行政处罚
- `qcc-risk.get_equity_pledge_info` — 股权质押
- `qcc-ipr.get_trademark_info` — 商标
- `qcc-ipr.get_internet_service_info` — ICP/APP/算法备案
- `qcc-operation.get_news_info` — 新闻

## 关键注意事项

1. **必须使用完整公司全称**（用工商登记全称，不用简称或品牌名）
2. 工具名使用 snake_case（如 `get_company_registration_info`）
3. 失败返回 `{"无匹配项": "未查询到匹配记录"}`
4. 单次查询约1-2秒/工具

## 缓存数据结构

qcc_cache.json 结构：
```json
{
  "project_name": "",
  "query_date": "",
  "basic_info": {},
  "shareholders": {},
  "equity_changes": [],
  "risks": {"litigation": [], "penalties": [], "dishonest": [], "alerts": []},
  "ip": {"patents": [], "trademarks": [], "copyrights": []},
  "operations": {"financing": [], "tenders": [], "investments": []},
  "inconsistencies": [],
  "findings_summary": ""
}
```
