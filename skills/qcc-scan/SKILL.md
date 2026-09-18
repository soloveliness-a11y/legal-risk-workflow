---
name: qcc-scan
description: |
  尽调数据采集规范（数据源无关）— 定义"工商信息怎么查、查什么、结果怎么结构化"的采集规范。
  查询执行者可以是自动适配器（如企查查 CLI），也可以是人工（国家企业信用信息公示系统等公开渠道）；
  无论何种来源，统一产出 qcc_cache.json + findings_summary.json，供 dd-prep/dd-check/risk-report/post-invest-check 直接引用。
  触发词：企查查、工商查询、尽调采集、工商扫描、qcc-scan；旧称 qcc_scan
metadata:
  version: "2.0"
  bundle: "0.3.0"
  tags: "私募, 风控, 尽调, 数据采集, 能力型, 跨阶段"
---
# qcc-scan — 尽调数据采集规范

## 定位

数据源无关的尽调数据采集规范，不属于任何特定 Phase。由 `risk-workflow` 编排器或父技能（dd-prep / dd-check / post-invest-check 等）按需调用。

本技能回答三个问题：

1. **查什么** — 采集维度清单（必查 / 按需 / 高管画像）
2. **怎么解读** — 6 项风险信号解读规则
3. **结果长什么样** — 统一产出 schema（qcc_cache.json + findings_summary.json）

**核心设计：采集意图与执行者解耦。** 每个维度只定义"采集意图 + 来源字段"；人工与自动采集填同一 schema，下游 diff / 复查 / 消费零改动。

执行者两种模式：

- **手工采集模式**（默认可用，零外部依赖）— 见下文专章
- **企查查 CLI 适配器**（可选示例，有 API 权限者）— 见下文专章

> 文件名 `qcc_cache.json` 是工作流数据总线的统一约定（CONTRACT §1 / §7.1），与具体数据源无关；手工采集同样写这个文件名。

**契约引用：** [../risk-workflow/CONTRACT.md](../risk-workflow/CONTRACT.md) §7.1（工商数据源适配器）、§2.3（确定性标签）、§4.2（子确认）、AC3（来源标注）、AC5（降级显式化）。

---

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| company_name | string | ✅ | 公司完整工商全称（不接受简称；简称须先验证全称）。**注意：公司可能已股改/更名**（如"有限公司"→"股份有限公司"），多维度查询全部返回"无匹配"时优先怀疑名称已变，用实体识别工具按信用代码或关键词反查现名 |
| scope | string | ❌ | `basic`（必查维度，默认）/ `extended`（必查 + 按需 + 高管画像，画像按触发条件执行） |
| output_dir | string | ✅ | 采集结果存放目录 |
| existing_cache | string | ❌ | 已有 qcc_cache.json 路径（增量更新场景） |
| persons | string[] | ❌ | 高管画像对象名单（未提供时先取主要人员名单） |

---

## 采集维度清单

维度与具体工具解耦：每个维度 = 一份采集意图。自动模式由适配器映射到对应查询；手工模式按公开渠道逐项人工查询（见"手工采集模式"）。

### 一、必查维度（scope=basic，法律尽调基线）

| # | 维度 | 采集意图 | 填入 cache 字段 |
|---|------|---------|----------------|
| 1 | 工商登记 | 注册信息、法定代表人、注册资本、成立日期、经营状态、经营范围 | items.basic_info |
| 2 | 企业概况 | 主营业务、行业分类、企业规模 | items.profile |
| 3 | 股权结构 | 全体股东、持股比例、认缴出资 | items.shareholders |
| 4 | 主要人员 | 董监高名单与职务 | items.key_personnel |
| 5 | 工商变更 | 历次变更事项与日期（重点：股权、法代、注册资本） | items.equity_changes |
| 6 | 对外投资 | 被投企业、持股比例、状态 | items.external_investments |
| 7 | 分支机构 | 分支机构名单与状态 | items.branches |
| 8 | 行政处罚 | 处罚记录、机关、金额、日期 | items.risks.penalties |
| 9 | 专利 | 数量、类型、法律状态 | items.ip.patents |
| 10 | 软件著作权 | 数量、登记日期 | items.ip.software_copyrights |
| 11 | 诉讼立案 | 在册立案、案由、当事人角色 | items.risks.litigation |

### 二、按需维度（scope=extended 追加）

| 维度 | 采集意图 | 填入 cache 字段 | 典型触发 |
|------|---------|----------------|---------|
| 股权出质 | 出质登记、质权人、状态 | items.risks.equity_pledge | 股权融资 / 股东资金压力线索 |
| 失信被执行 | 失信记录、执行法院、涉案金额 | items.risks.dishonest | 信用核查 |
| 商标 | 注册商标、类别、状态 | items.ip.trademarks | 品牌型业务 |
| 网络服务备案 | ICP / APP / 算法备案 | items.operations.internet_services | 互联网业务 |
| 融资历史 | 历轮融资、时间、投资方 | items.operations.financing | 建议全场景采集 |
| 新闻舆情 | 近期正负面报道 | items.operations.news | 舆情线索 |
| 招投标 | 中标记录 | items.operations.tenders | To B / 政府客户业务 |

### 三、高管画像维度（条件触发，scope=extended）

> **触发条件（满足任一即执行）：**
> - dd-prep 风险假设中包含竞业限制 / 职务发明 / 利益冲突相关假设
> - 公司有多名核心人员来自同一家前雇主
> - 用户明确要求核查董监高背景
> - 投后定期扫描场景（post-invest-check）

采集意图（对每位核心人员）：

| 画像面 | 采集内容 |
|--------|---------|
| 任职与控制 | 当前在外任职、全部关联企业、担任法定代表人的企业、实际控制的企业、对外投资 |
| 涉诉与诚信 | 法院立案、被执行、失信、裁判文书 |
| 资产风险 | 股权出质、股权冻结、限制高消费、限制出境 |
| 合规 | 行政处罚、税收违法 |
| 历史追溯（投后/变更检测场景） | 历史任职、历史关联企业、历史投资 |

填入 `items.executives.profiles[]`（结构见产出 schema）。

**画像执行规则：**
- 需先取得主要人员名单（必查维度 4），再逐人采集
- 任职与控制面 5 项为画像核心，触发时必采；其余各面按需
- 人名查询不匹配时，回退名单核对准确姓名后重采

---

## 6 项风险信号解读规则（数据处理必做）

采集完成后的固定处理动作，手工与自动模式一致；处理结果落入 findings_summary，不改动原始采集数据。

| # | 处理项 | 识别的风险信号 | 解读要点 |
|---|--------|--------------|---------|
| 1 | 股权结构图谱 | **代持 / 一致行动 / 境外实体** | 股东为自然人但与董监高名单不重叠 → 疑似代持；多名股东同地址、同批次入股 → 疑似一致行动；架构含境外层级 → 标注入境合规审查需求 |
| 2 | 诉讼/处罚统计 | 数据与投资建议书（公司自述）不符 | 与 [BP声称] 口径逐项对照，差异标 ⚠️不一致，不自行判定哪方正确 |
| 3 | IP 数量/类型统计 | IP 实力与业务叙事不符 | 核心技术公司专利/软著数量过低、或大量失效 → 权属与业务独立性疑点 |
| 4 | 融资时间线 | **特殊权利到期情况** | 逐轮标注优先清算/回购/反稀释等特殊权利的起算与到期点，输出"未来 12 个月到期权利"清单 |
| 5 | 股权出质/冻结/限制 | 股东层面资产受限 | 任何出质/冻结/限高记录 → severity 取最高档（关注高），逐条列明 |
| 6 | 对外投资/分支 | 关联方识别 | 与主营业务无关的对外投资、非经营目的分支机构 → 列入关联方清单，供 dd-check 交叉比对 |

---

## 统一产出 schema

遵循 [CONTRACT §7.1](../risk-workflow/CONTRACT.md)。两份产物，任何来源填同一结构。

### 1. qcc_cache.json（原始数据缓存，数据源无关）

```json
{
  "schema_version": "2.0",
  "company_name": "<完整工商全称>",
  "scope": "basic | extended",
  "query_date": "<ISO 日期>",
  "source": "manual | qcc-cli | <其他适配器标识>",
  "query_log": [ { "channel": "<渠道/工具>", "url_or_command": "<查询记录>", "date": "<ISO>", "operator": "<人工/技能名>" } ],
  // 提示：risk_screener.py 等脚本读取 CONTRACT §7.1 的平铺字段（basic_info/shareholders/risks），
  // 与 items.* 需同时填写（双写）；文档交叉源证据放 document_evidence 扩展段
  "items": {
    "basic_info": {}, "profile": {}, "shareholders": {}, "key_personnel": [],
    "equity_changes": [], "external_investments": [], "branches": [],
    "risks": { "litigation": [], "penalties": [], "dishonest": [], "equity_pledge": [], "alerts": [] },
    "ip": { "patents": [], "trademarks": [], "software_copyrights": [] },
    "operations": { "financing": [], "tenders": [], "news": [], "internet_services": [] },
    "executives": {
      "scanned_persons": [],
      "profiles": [
        { "name": "", "positions": [], "related_companies": [], "controlled_companies": [],
          "legal_rep_roles": [], "investments": [],
          "litigation": {}, "asset_risks": {}, "compliance": {}, "historical": {} }
      ]
    }
  },
  "uncovered": [ { "dimension": "<维度名>", "reason": "<未采到原因>" } ],
  "inconsistencies": []
}
```

- `source` 必填：手工采集填 `manual`；适配器填其标识
- `query_log` 记录每次查询动作（渠道 + 日期 + 操作者），手工模式强制，自动模式可由命令记录生成
- `uncovered`：任何维度未采到必须显式登记原因（AC5），禁止以沉默冒充无风险
- 各维度内部结构按原始记录填写，不做二次加工

### 2. findings_summary.json（结构化发现摘要，独立文件）

```json
[
  {
    "category": "主体与股权 | 诉讼风险 | 知识产权 | 经营异常 | 行政处罚 | 融资历史 | 关联关系 | 高管画像",
    "item": "<具体发现事项>",
    "severity": "关注高 | 关注中 | 关注低",
    "fact": "<事实描述，含数字与日期>",
    "source_ref": "<指向 qcc_cache 对应字段或 query_log 记录>"
  }
]
```

**规则（格式硬验收）：**

- 必须为**数组**，每项为 dict；禁止按严重度分组的 dict 形态
- 仅收录需关注的问题与不一致处，不含全量正常数据
- 5 个字段（category / item / severity / fact / source_ref）缺一不可；severity 三档为 CONTRACT §7.1 统一口径
- **severity ≠ 最终风险评级**——仅表示数据层面的关注程度，评级是 risk-report 的职责
- 无 source_ref 的发现视为不合规（等同 AC3 不通过）

### 子确认（可选，遵循 CONTRACT §4.2）

- **启动时**：向审批人展示公司全称、scope、采集方式（手工 / 适配器）与预计耗时，口头确认即可，记一行 project_log
- **完成时**：按 category 分组展示 findings 摘要（每类 1-2 条）+ 高影响发现（股东变更 / 诉讼 / 处罚 / 质押 / 冻结），确认后进入 Dossier 更新与下游使用

---

## 手工采集模式（默认可用）

零外部依赖：按维度清单逐项人工查询公开渠道，填入同一 qcc_cache.json（`source: "manual"`），再按 6 项信号规则产出 findings_summary。

### 公开渠道对照表

| 维度组 | 首选公开渠道（免费） | 备注 |
|--------|--------------------|------|
| 工商登记 / 股东 / 变更 / 分支 / 行政处罚 / 经营异常 / 年报 | 国家企业信用信息公示系统（gsxt.gov.cn） | 手工模式首选 |
| 诉讼立案 / 裁判文书 / 法院公告 | 中国裁判文书网、人民法院公告网 | 案号可交叉验证 |
| 失信 / 被执行 / 限高 | 中国执行信息公开网 | 自然人股东同样可查 |
| 专利 | 国家知识产权局专利检索系统 | 法律状态逐条核对 |
| 商标 | 中国商标网 | |
| 软件著作权 | 中国版权保护中心登记公告 | |
| 融资 / 舆情 / 招投标 / 备案 | 通用搜索 + 行业媒体 + 上市公司公告平台 | 非官方渠道，来源逐条落 query_log |

### 操作示例（以"股权结构"维度为例）

1. 打开国家企业信用信息公示系统，输入已验证的公司全称，进入企业详情页
2. 逐项抄录"股东信息"栏目：股东名称、持股比例、认缴出资额 → 填 `items.shareholders`
3. 切到"股权变更记录"，逐条抄录变更日期与前后持股 → 填 `items.equity_changes`
4. 在 `query_log` 登记本次查询：渠道（gsxt.gov.cn）、查询日期、操作人
5. 抄录中发现的疑点（如某股东与董监高名单不重叠）暂记 `inconsistencies`，交信号规则 1 正式解读
6. 该维度即完成；其余维度同法逐项推进，每完成一组即落盘保存，避免浏览器会话中断丢数据

**手工模式纪律：**

- 每条数据必须可回溯到 query_log 记录，否则等同无 source
- 查不到的维度填 `uncovered`，写明具体原因（"公示系统无此栏目" / "检索无结果"）
- 抄录数字禁止约数化（CONTRACT §2.3 标签纪律）

---

## 企查查 CLI 适配器（可选示例）

有企查查 API 权限的环境可用 CLI 自动采集，替代人工逐项查询。适配器与手工模式完全等价：同一维度清单、同一 cache schema。

### 调用意图

- **单参数查询**（按企业）：`qcc <分组> <工具> "<企业全称>"` — 覆盖必查维度（登记 / 概况 / 股东 / 人员 / 变更 / 投资 / 分支 / 处罚 / 专利 / 软著 / 立案）与按需维度（出质 / 失信 / 商标 / 备案 / 融资 / 舆情 / 招投标）
- **双参数查询**（企业 + 人名）：`qcc executive <工具> --searchKey "<企业全称>" --personName "<人名>"` — 覆盖高管画像全部维度
- 画像触发条件与执行规则见"高管画像维度"章节

### 配额与采集纪律

- CLI 与 MCP 通道若共享账户配额，积分耗尽（如 error 300008/100211）时：按 CONTRACT AC5 显式登记 uncovered，用公司文档 + 公开渠道（裁判文书网/信用公示系统）交叉补位，不阻塞流程
- **先落盘再展示**：CLI 输出可能被截断（如关联企业只回传前 60 条），采集结果必须先写入 raw_ 存档文件再引用，禁止只凭会话内可见摘录入底稿

### 批量编排（可选）

工作区可配批量编排脚本（存在时可用）：`{workspace}/scripts/orchestrators/qcc_batch_scan.py`（plan 生成任务清单 → 逐步执行 → sync 回写 cache → summary 摘要）；缓存读写与格式校验可用 `{workspace}/scripts/tools/qcc_cache_manager.py`。脚本不存在时逐条调用或转手工模式，不阻塞流程。

### 异常处理（适配器模式）

| 场景 | 处理动作 |
|------|---------|
| CLI 不可用 | 切换手工采集模式，cache 标注 `source: "manual"` |
| 单项超时 | 跳过并登记 `uncovered`（reason: timeout）；同组≥3 项超时 → 暂停告知审批人 |
| 返回空数据 | 重试 1 次（换相近查询）；仍空 → 登记 `uncovered`（reason: no_data），不阻塞 |
| 人名不匹配 | 回退主要人员名单核对姓名后重调 |
| 简称 / 多结果匹配 | 先验证全称；无法确定 → 给审批人候选列表确认 |

---

## 缓存新鲜度与增量复查（两种模式通用）

- **复查触发**：距 `query_date` > 7 天且项目处于报告撰写或复核阶段 → 全量重采（与首次同 scope）
- **增量 diff**（投后定期扫描 / 传入 existing_cache）：新增项 `[NEW]`、变更项 `[CHANGED]`、消失项 `[REMOVED]`、不变项保留
- **diff 产物**：`{output_dir}/qcc_review_diff.json` — 逐字段记录 section / field / old_value / new_value / change_type / requires_review，附汇总统计（total / added / modified / removed / high_impact）
- **Dossier 回填**：`requires_review: true` 的变更 → 对应 Dossier 字段标 📌待核实；高影响变更（股东变更、新增诉讼、新增处罚、新增质押/冻结）→ 提请审批人确认后更新 certainty 与 source

---

## 跨 Phase 调用场景

| Phase | 调用方 | scope | 说明 |
|-------|-------|-------|------|
| Phase 1 | dd-prep | basic（默认） | 首次全量采集，建立基线 |
| Phase 1 | dd-prep | extended（含画像） | 核心人员竞业/利益冲突核查（触发条件见高管画像维度） |
| Phase 2 | dd-check | basic | 交叉验证公司回复材料 |
| Phase 3 | risk-report | 不采集 | 读取已有 qcc_cache.json |
| Phase 6 | post-invest-check | basic / extended + 增量 | 定期扫描，与历史 cache 比对 |

---

## 降级

遵循 [CONTRACT AC5](../risk-workflow/CONTRACT.md)：任何数据源不可用（无 API、无网络、公示系统维护）时，产出中必须显式标注「本维度未核查，原因：…」并落入 `uncovered`，禁止以沉默冒充无风险。零外部依赖环境以手工模式为默认路径。

---

## 质量检查

- [ ] 公司全称为完整工商全称（已验证非简称）
- [ ] qcc_cache.json 已生成、非空，`source` 与 `query_log` 已填
- [ ] 必查维度全部有数据或已登记 uncovered
- [ ] scope=extended 时高管画像已按触发条件执行（未触发需注明理由）
- [ ] 6 项数据处理已完成，结果落入 findings_summary
- [ ] findings_summary 为数组，每项 5 字段齐全，severity 三档口径
- [ ] 每条发现有 source_ref；无来源发现 = 不通过
- [ ] 降级维度均已显式登记（AC5）
- [ ] 增量场景变更项已标注 [NEW]/[CHANGED]/[REMOVED]

---

## 版本

当前版本以 frontmatter `version` 为准；完整版本历史见 [CHANGELOG.md](./CHANGELOG.md)。
