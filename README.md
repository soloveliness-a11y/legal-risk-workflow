# legal-risk-workflow

一套面向 PE/VC 法律尽调与投后工作的 Agent 工作流。它把尽调准备、资料核查、访谈纪要、风险报告、报告复核、交易文件和投后跟踪等环节拆成可组合的技能，并用共享的数据结构和交付检查连接起来。

这不是一个独立运行的软件，也不提供法律结论。它更适合已经具备法律、投资或风控经验，且希望把重复性工作交给 AI Agent 处理的使用者。

## 能做什么

当前仓库包含 1 个主编排器、10 个业务能力技能和 1 个工作流复盘元技能：

- 尽调准备：形成风险假设、资料清单和访谈提纲
- 工商与公开信息采集：支持外部数据适配器，也支持手工采集
- 行业与专项研究：按问题组织检索，并保存来源记录
- 法律法规核查：围绕具体问题检索现行法源，避免直接依赖模型记忆中的条号和版本
- 资料核查：对股权、主体、知识产权、诉讼、高管等信息进行结构化比对
- 访谈纪要：在保留人名、数字、日期和限定条件的基础上整理文字
- 风险报告：基于已记录事实形成风险分析、风险矩阵和投资建议部分
- 报告复核：检查事实、来源、风险等级、表述和跨文档一致性
- 交易文件：将风险事项映射到协议条款，并检查前轮权利保全
- 投后跟踪：维护法律台账、预警事项和风险传导记录
- 工作流复盘：记录执行中暴露的问题，为后续维护提供输入

其中 risk-workflow 是主入口和共享契约的持有者；其余技能通过文件系统中的约定文件衔接。完整的技能清单和说明见 [使用指南](./docs/AI_Agent_Risk_Workflow_分享文档.md)。

## 设计要点

### 主干固定，分支有限

工作流规定了尽调启动、报告定稿、交易与投后基线三个必须由人放行的检查点；尽调收口默认随报告初稿一并审批，只在存在足以改变核心结论的缺口时单独停下等待决定。Agent 可以在明确的分支点提出补充调查、补充材料或终止建议，但不会替审批人作出最终风险判断。

### 用交付检查约束结果

各技能不要求使用者逐步监督每一次模型调用，而是要求交付前检查几类容易出错的问题：

- 关键事实是否能回溯到材料和证据登记
- 风险矩阵、报告正文和下游文件是否相互对应
- 数字、日期、主体名称和风险编号是否一致
- 无法核查的事项是否明确写成未核查，而不是默认为无风险
- 研究类结论是否保存了来源和访问日期

这些检查能减少常见的遗漏和改写失真，但不能替代专业判断或事实核验。

### 共享工作区

项目文件保存在如下结构中：

    projects/{项目名}/
    ├── project_dossier.md
    ├── evidence_registry.json
    ├── project_log.md
    ├── 01_dd_prep/
    ├── 02_dd_check/
    ├── 03_dd_interview/
    ├── 04_risk_report/
    ├── 05_report_review/
    ├── 06_txn_docs/
    ├── 07_post_invest/
    └── research/

project_dossier.md 是跨技能使用的工作视图；关键事实还应能回溯到 evidence_registry.json 中登记的证据。具体字段、状态标签、检查点和验收要求以 [CONTRACT.md](./skills/risk-workflow/CONTRACT.md) 为准。

## 快速开始

### 1. 将仓库放入 Agent 的工作区

本仓库是一个 bundle。使用单个子技能时，也要一并提供：

- skills/risk-workflow/CONTRACT.md
- 该技能引用的知识库文件
- templates/ 和需要使用的脚本

不同宿主的接入方式可能不同：

| 宿主 | 建议方式 |
| --- | --- |
| Claude Code | 将 skills/ 下的目录复制到 ~/.claude/skills/ 或项目级技能目录 |
| Codex 或其他支持 .agents/skills 的环境 | 仓库根目录已内置 `.agents/skills`（指向 skills/ 的符号链接），克隆后即可自动发现；不支持符号链接的环境改为复制 |
| 其他 Agent | 保留 skills/、knowledge-base/、templates/ 和 scripts/ 的相对关系 |

无论采用哪种方式，复制到宿主目录只用于技能发现；技能运行时依赖仓库根目录的 `scripts/`、`templates/`、`knowledge-base/`，因此完整仓库必须保留在原位，技能中出现的 `{workspace}` 均指仓库根目录。

### v0.2.0 技能重命名

自 v0.2.0 起，技能目录与 `name` 字段统一为小写连字符（对齐 Agent Skills 规范）：dd_prep→dd-prep、dd_check→dd-check、dd_interview→dd-interview、risk_report→risk-report、report_review→report-review、txn_docs→txn-docs、post_invest_check→post-invest-check、qcc_scan→qcc-scan、industry_research→industry-research、legal_research→legal-research。旧下划线名称保留为各技能描述中的检索别名；版本号移至 `metadata.version`（字符串）。项目工作区的阶段目录（01_dd_prep 等）是数据布局约定，不随技能重命名。

### 2. 配置可选适配器

    cp config.example.yaml config.yaml

OCR、工商数据源和第二信源适配器都可以不配置。未配置时，核心链路使用手工采集或人工核查，并在输出中标明限制。

### 3. 运行环境检查

需要 Python 3.10 及以上。脚本针对 macOS/Linux 编写，Windows 建议在 WSL 或 Git Bash 中运行。

    python3 -m pip install -r requirements/core.txt
    bash scripts/first_run.sh

完成后，可以向 Agent 发出“启动新风控项目”或“继续 {项目名}”等指令。想先用一套完全虚构的材料看 Phase 1 跑通的样子，见 [examples/synthetic-demo](./examples/synthetic-demo/)。脚本和配置的进一步说明见 [scripts/README.md](./scripts/README.md)。

## 输出物说明

一个项目完整走完后，`projects/{项目名}/` 下会有：项目 Dossier（权威工作视图）、证据登记（evidence_registry.json）、项目日志（含人工检查点审批记录）、尽调清单与核查表、访谈纪要、风控报告（md，可转 docx）与风险矩阵、复核意见、交易文件条款落实三件套、投后法律台账。默认呈报只突出报告与关键待核实事项，其余底稿经产物索引按需查阅。各阶段的验收要求（来源标注、跨文档一致性、降级显式化等）见 [使用指南](./docs/AI_Agent_Risk_Workflow_分享文档.md) 第 6 节，机械校验一条命令：

    python3 scripts/validate_delivery.py projects/{项目名}/

## 支持矩阵与限制

| 能力 | 状态 |
| --- | --- |
| 核心链路（清单、核查、纪要、报告、复核、交易文件、投后台账） | 可用，无外部依赖 |
| 报告 .docx 输出 | 需 python-docx（requirements/core.txt） |
| 工商数据自动采集 | 可选：企查查 CLI 适配器；默认手工采集模式 |
| 扫描件 OCR | 可选外部适配器；敏感材料默认禁止上传外部服务（本地 OCR 或人工转录），已核验服务商保密与不训练承诺的可在 config 开启信任路径（[SECURITY_PRIVACY.md](./SECURITY_PRIVACY.md)） |
| 法源核验 | 可选适配器；无适配器时人工查官方文本并标注来源 |
| 已验证范围 | 有限样本回归测试，覆盖不同项目阶段与工作流环节（[EVALUATION.md](./docs/EVALUATION.md)）；投后检查、多场访谈综合、CLI 适配器覆盖有限 |
| 不提供 | 法律意见、真实项目数据、可直接签署的交易文件范本 |


## 仓库结构

    skills/            主编排器和能力技能（.agents/skills 符号链接供宿主发现）
    knowledge-base/    行业检查库、风险主题、参考规范和写作资料
    templates/         Dossier、清单、访谈、报告和交易文件模板
    scripts/           环境检查、交付校验及可选适配器脚本
    docs/              使用指南、评估说明、排除项和开发记录
    evals/             测试用例与评估材料
    examples/          合成演示（完全虚构）

知识库按需加载，不要求每次执行都读取全部内容。案例学习笔记目录用于使用者自建的私有材料；仓库不提供项目级案例文件。

## 有限的回归测试

维护者已进行有限样本回归测试，覆盖不同项目阶段与尽调、投后的主要工作流环节，检查覆盖情况、信息保真和契约执行情况。聚合验证结果和未充分验证项见 [EVALUATION.md](./docs/EVALUATION.md)。

这些结果只说明该版本在有限样本上的测试情况，不代表一般准确率、风险识别率或对其他行业和项目的保证。尤其是投后检查、多场访谈综合和外部 CLI 适配器，公开评估中的覆盖仍然有限。使用者应使用自己的材料和标准进行独立验证。

## 公开范围与匿名化

公开版本仅保留通用方法、空白模板及明确标注的教学示例：

- 不包含真实项目的原始材料、报告、访谈记录或项目级事实链；此类材料由使用者自行管理，保存在公共仓库之外
- 行业检查点和风险主题为条件式核查问题，不以特定公司的项目事实作为运行前提
- 使用者自行加入的项目材料应保存在私有工作区，不要提交到公共仓库
- 向本仓库新增内容前，应结合文件组合和具体措辞做人工复核（发布范围规则见 [EXCLUSIONS.md](./docs/EXCLUSIONS.md)）

## 许可

- scripts/ 下的代码：MIT
- 技能、知识库、模板和文档：CC BY 4.0

详见 [LICENSE](./LICENSE)、[LICENSE-CONTENT](./LICENSE-CONTENT) 和 [NOTICE.md](./NOTICE.md)。

## 免责声明

本仓库提供的是工作流和方法论参考，不构成法律意见、投资建议或事实核查结论。AI 生成的尽调结论、风险评级、报告和交易文件均须由具备相应经验和权限的专业人员独立复核；使用者自行承担使用、修改和对外依赖相关的责任。

欢迎通过 Issue 或 Pull Request 提交问题和改进建议。

---

作者：A1np
