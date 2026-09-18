# NOTICE — 双许可划分

本仓库采用双许可证，按内容类型划分：

| 内容 | 许可证 | 范围 |
|------|--------|------|
| **代码** | [MIT](./LICENSE)（标准 MIT 全文，无修改） | `scripts/`（tools / capabilities / docx_engine / orchestrators / infra / reference、first_run.sh、config_loader.py、validate_delivery.py）、`.github/workflows/` |
| **文本内容** | [CC BY 4.0](./LICENSE-CONTENT)（含完整法律文本） | `skills/`、`knowledge-base/`、`templates/`、`commands/`、`docs/`、`evals/`、`examples/`、`README.md`、`CONTRIBUTING.md`、`SECURITY*.md` 及根目录其他 md 文档 |

划分细则：

- 边界以目录为准；`scripts/reference/` 中的 Markdown 参考存档按文本内容（CC BY 4.0）归类。
- 同一文件中如同时包含脚本与说明性内容，按其主体属性归类。
- 配置模板 `config.example.yaml` 按 MIT 归类；用户本地的 `config.yaml` 不随仓库分发。

第三方注意事项：

- `knowledge-base/` 中的行业检查要点、法规索引为公开信息整理，引用具体法条时请以现行有效版本为准（法规修订频繁；刚性数值来源登记见 `knowledge-base/法律数字来源索引.md`）
- 公开范围：本仓库仅包含通用方法、空白模板与明确标注的示例，真实项目材料不随包分发（发行范围说明见 [README.md](./README.md)）；向本仓库贡献内容前须完成发布范围审核（见 [docs/EXCLUSIONS.md](./docs/EXCLUSIONS.md)）
- 外部数据源（工商数据源 CLI、OCR 服务等）为可选适配器，使用时遵循各自的服务条款与数据合规要求（数据分级见 [SECURITY_PRIVACY.md](./SECURITY_PRIVACY.md)）

Copyright (c) 2026 A1np
