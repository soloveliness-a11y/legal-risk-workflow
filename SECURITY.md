# SECURITY.md

本仓库是一个法律风控工作流技能包，不含服务器或在线服务，安全边界主要在数据处理与内容正确性两端。

## 报告安全漏洞

- 范围：脚本中的凭据处理缺陷、路径穿越、不安全默认值；技能流程中可能导致敏感材料外泄的数据流问题。
- 渠道：GitHub 仓库的 Security Advisories（Report a vulnerability）；不便使用时开 issue 并先脱敏。
- 请勿在报告中粘贴真实凭据、真实客户数据或项目材料；最小化复现信息即可。
- 修复发布前请勿公开披露细节。

## 报告法律内容错误

本仓库的知识库与示例含法律、监管、交易所规则表述，错误表述可能误导使用者。

- 请指出文件与行号、现行有效的官方来源（文号/官方链接）、正确表述。
- 维护侧按 `knowledge-base/法律数字来源索引.md` 的登记规范补来源元数据后修正。
- 争议条款以现行有效的官方文本为准，不以本仓库表述为准（见 README 免责声明）。

## 敏感数据处理

提交 issue、PR 或任何公开讨论时，禁止粘贴真实项目材料：客户名称、案号、工商可查事实组合、合同文本、员工名册、财务数据、访谈内容。具体数据分级与默认本地处理原则见 [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md)。

## 维护侧自检

提交前运行（含 CI）：

```bash
python3 scripts/tools/release_scan.py             # 工作树：匿名化与凭据扫描（可配置私有词表）
python3 scripts/tools/release_scan.py --history   # 发布前加扫：git 历史文件快照 + commit/tag message
```

扫描能力边界：

- 默认只扫描工作树（跳过 `.git`）；`--history` 才覆盖本地 git 历史（全部可达文件快照、commit message、tag message）
- GitHub Release 文案、Issue、PR、Wiki 只存在于远端，脚本无法覆盖：每次发布前人工复核 Release 正文与近期 issue/PR 措辞，确认不含私有词与内部样本构成信息
- 已推送后又在远端丢弃或改写的对象不在本地仓库，`--history` 无法覆盖

私有词表（公司名/项目名等）只保存在仓库外，经 `--wordlist` 或 `config.yaml` 的 `security.wordlist` 引入；禁止把私有词以明文 denylist 形式提交进本仓库。
