# CONTRIBUTING — 贡献指南

感谢参与。本仓库面向法律工作者的 Agent 风控工作流，贡献前请先读 [README.md](./README.md) 的免责声明与 [SECURITY_PRIVACY.md](./SECURITY_PRIVACY.md) 的数据分级——**任何真实项目材料都不得进入 issue、PR 或讨论**。

## 提交 issue

- 缺陷：给出复现步骤、涉及文件与行号、运行环境（宿主 / Python 版本）。
- 不要粘贴客户名称、案号、合同文本、员工名册、财务数据、访谈内容；用占位符（如"某公司 A"）替代。
- 法律内容错误请用下方模板一。

## 法律内容纠错（issue 模板一）

```markdown
## 法律内容纠错
- 文件与位置：knowledge-base/xxx.md 第 N 行（或 skills/xxx/SKILL.md）
- 现文表述：<原句>
- 问题：<名称/条号/数值/时效/适用条件有误>
- 正确表述：<建议表述>
- 官方来源：《法规全名》（文号），施行/适用期；官方链接：<URL>
```

维护侧处理规则：核对官方来源 → 修正表述并在 `knowledge-base/法律数字来源索引.md` 登记来源元数据（来源名称、文号、施行/适用期、官方渠道、核验日期）；无法定位权威来源的数值改为运行时核验提示，不保留硬编码数值。

## 隐私披露（PR 必填，模板二）

每个 PR 描述中必须包含以下声明并逐项确认：

```markdown
## 隐私披露
- [ ] 本 PR 不含真实客户、项目、联系人或业务数据
- [ ] 不含案号、信用代码、精确项目日期等可检索指纹
- [ ] 示例均为虚构或已明确标注的公开资料
- [ ] 已自查内容组合（行业+轮次+金额量级+结局）不指向现实单一主体
```

## PR checklist

- [ ] 隐私披露（模板二）已填写并全部勾选
- [ ] `python3 -m compileall -q scripts` 通过
- [ ] `python3 scripts/tools/validate_skills.py` 通过（改了 SKILL.md 时必查）
- [ ] `python3 scripts/tools/release_scan.py` 通过（建议配置私有词表后运行）
- [ ] `python3 scripts/validate_delivery.py` 在示例项目上无新增 FAIL（改了交付链路时必查）
- [ ] `pytest -q`（测试套件）通过
- [ ] 新增精确法律/监管/交易所数值已登记 `knowledge-base/法律数字来源索引.md`
- [ ] 文档口径与 README/EVALUATION 一致（预警类别数、模块数量、技能名等）

## 内容边界（详见 [docs/EXCLUSIONS.md](./docs/EXCLUSIONS.md)）

- 只收通用方法、空白模板、独立构造并明确标注的示例
- 案例经验一律先落私有库；公共库接受的是去个案化后的通用规则
- 新增技能/知识条目不得引用具体项目的未公开状态

## 代码贡献

- 脚本仅依赖 Python 标准库 + requirements/core.txt 中的依赖；新依赖先进 `requirements/` 对应分层文件并说明理由
- 外部服务调用必须默认关闭、显式确认开启（对照 SECURITY_PRIVACY.md 第 2 节）
- 保持 CLI `--help` 可用且退出码 0；新增 CLI 记得加入 `scripts/first_run.sh` 的自检清单
