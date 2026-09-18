# 启动新风控项目

> 快捷命令：启动风控项目，从 dd-prep 开始全流程。

## 触发方式

用户说"启动新风控项目"、"开始尽调"、"新风控项目"等。

## 执行流程

1. 询问以下信息：
   - 项目名称（被投企业全称）
   - 投资阶段（天使/Pre-A/A/B/C/Pre-IPO/定增/基石/二轮）
   - 小预审材料路径
   - 是否有前轮尽调报告？（如有，提供路径）
   - 所属细分赛道
   - 项目类型（直投/投顾/S基金/子基金）

2. 创建项目骨架（必须先于任何 Skill 调用——dd-prep 启动即需向项目目录写文件）：
   `mkdir -p {workspace}/projects/{project_name}/`，包含：
   - 阶段目录：00_raw / 01_dd_prep / 02_dd_check / 03_dd_interview / 04_risk_report / 05_report_review / 06_txn_docs / 07_post_invest / 99_archive / research
   - `project_dossier.md`：从 `templates/project_dossier_template.md` 复制，填入项目名称与投资阶段
   - `evidence_registry.json`：初始化为 `{"claims": {}, "evidence": []}`
   - `project_log.md`：创建项目日志，记录启动时间、项目名称与阶段
   - 状态文件的字段语义见 `skills/risk-workflow/CONTRACT.md`

3. 调用 risk-workflow Skill（阶段划分、检查点与产出契约见 `skills/risk-workflow/CONTRACT.md`），启动 dd-prep。

4. dd-prep 编排 qcc-scan + industry-research，生成清单（外部版+内部版）。

## 对应 Skill

- risk-workflow（主编排器，契约见 `skills/risk-workflow/CONTRACT.md`）→ dd-prep（尽调启动引擎，编排 qcc-scan + industry-research）
