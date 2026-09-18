# 启动新风控项目

> 快捷命令：把材料交给工作流，说明要解决什么决策问题，先得到报告草稿和关键待核实事项。

## 触发方式

用户说"启动新风控项目"、"开始尽调"，或直接给出项目材料并要求风控判断。

## 执行流程

1. **只问一次、只问两件事**（其余信息不阻塞启动）：
   - **材料在哪**：BP/投资建议书/工商截图/已有尽调报告等材料路径，至少一份；完全没有材料时不启动，向用户说明原因
   - **要解决什么决策问题**（可选，缺省为"尽调 + 出风控报告"，如"能否上会""老股受让值不值得做"）

   项目工商全称无法从材料识别时补问一次。投资阶段、细分赛道、项目类型、前轮报告有无，一律从材料推断；推不出的按 dd-prep 缺省规则（成长期 + 直投 + 📌预判）处理。**不在启动环节逐项询问这些字段**——推断与缺省结果随 CP1 呈报，由审批人确认后回填。

2. 创建项目骨架（必须先于任何 Skill 调用——dd-prep 启动即需向项目目录写文件）：
   `mkdir -p {workspace}/projects/{project_name}/`，包含：
   - 阶段目录：00_raw / 01_dd_prep / 02_dd_check / 03_dd_interview / 04_risk_report / 05_report_review / 06_txn_docs / 07_post_invest / 99_archive / research
   - `project_dossier.md`：从 `templates/project_dossier_template.md` 复制，填入项目名称
   - `evidence_registry.json`：初始化为 `{"claims": {}, "evidence": []}`
   - `project_log.md`：创建项目日志，记录启动时间、项目名称与用户的决策问题
   - 状态文件的字段语义见 `skills/risk-workflow/CONTRACT.md`
   - 用户提供的外部材料归档到 `00_raw/`，工作产物只写各阶段目录

3. 调用 risk-workflow Skill（阶段划分、检查点与产出契约见 `skills/risk-workflow/CONTRACT.md`），启动 dd-prep。

4. dd-prep 编排 qcc-scan + industry-research，生成清单（外部版+内部版），经 CP1 人工审批后进入尽调。过程中的机械性确认默认合并进检查点呈报（CONTRACT §4.2），不逐项打断用户。

5. 报告初稿完成后，默认交付三件（CONTRACT §8.1）：报告草稿、关键待核实事项（按对结论影响排序）、产物索引（证据底稿按需查阅）。

## 对应 Skill

- risk-workflow（主编排器，契约见 `skills/risk-workflow/CONTRACT.md`）→ dd-prep（尽调启动引擎，编排 qcc-scan + industry-research）
