# 合成演示（synthetic-demo）

> ⚠️ **本目录全部内容为虚构**。"星洲微电子（苏州）有限公司"及其人员、股权、客户、数据均为教学示例构造，不对应任何现实主体；工商信息也不是任何真实查询的结果。可自由修改与分发（CC BY 4.0）。

## 这是什么

一套最小输入材料，用来在 3 分钟内看到工作流的 Phase 1 实际跑起来：从虚构的 BP 摘要与"手工采集"工商信息出发，产出尽调清单、风险假设与访谈提纲，并在 CP1 停下来等人工审批。

## 怎么跑

1. 按仓库 [README](../../README.md) 完成安装与 first_run。
2. 对你的 Agent 说：

   > 启动新风控项目，项目名 synthetic-demo，材料在 examples/synthetic-demo/materials/，走手工采集模式，工商数据直接用 materials/qcc_cache_manual.json。

3. Agent 应执行 Phase 1（dd-prep），结束后在 CP1 停止等待你确认。

## 预期产出

```
projects/synthetic-demo/
├── project_dossier.md        # 初始 Dossier（§0-§15 骨架 + 已知事实带确定性标签）
├── evidence_registry.json    # 初始证据登记
├── project_log.md            # 日志（含 CP1 待审批状态）
└── 01_dd_prep/               # checklist_*.md / risk_hypotheses.md / interview_outline.json / 初筛卡
```

不同模型与宿主的措辞会有差异，以下几点不应有差异（不符合即验收不过）：

1. 产出文件落在上述约定路径，output.json 的 status 为 completed 或 partial；
2. 风险假设能追溯到材料依据（BP 声称的内容带 [BP声称] 标签，不冒充已确认事实）；
3. 材料中没有的信息（如实缴资本、专利清单）出现在 pending 清单或标注"未提供"，而不是被编造；
4. CP1 未获人工确认前不进入 Phase 2。

## 材料里埋了什么

materials/ 两份文件中埋了几类常见信号，可用来对照风险假设的质量：创始人前雇主与竞业限制的表述、一处股权代持线索、单一客户高集中度、认缴与实缴的差距、一项"已申请"但状态不明的专利。跑完后可以检查：这些信号是否被假设覆盖，[BP声称] 与 ✅已确认 是否区分清楚。

## 不要做什么

- 不要把真实项目材料放进本目录或提交到仓库（见 [CONTRIBUTING.md](../../CONTRIBUTING.md) 隐私披露）；
- 不要期待产出一份完整报告：演示只覆盖 Phase 1，报告需要你补充材料并放行后续检查点。
