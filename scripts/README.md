# scripts/ 目录说明

> risk-workflow 辅助脚本集，按职责分层。核心依赖仅两项：python-docx（报告 .docx 输出）与 pyyaml（config 解析，缺失时回退内置简易解析器）；其余外部依赖（工商数据源 / OCR / 第二信源）均为**可选适配器**（CONTRACT §7），未配置时核心链路以手工采集模式跑通。

## 目录结构

```
scripts/
├── tools/              # CLI 入口脚本（Skill 直接调用）
├── capabilities/       # 原子能力模块（单职责，被 tools 引用）
├── docx_engine/        # Markdown→Word 转换引擎
├── orchestrators/      # 批量编排器
├── infra/              # 基座层（HTTP/浏览器/凭证）
├── reference/          # 官方示例等参考存档（Markdown，不参与编译）
├── first_run.sh        # 首次部署环境检查
└── README.md           # 本文件
```

## 统一验收入口

```bash
python3 scripts/validate_delivery.py projects/{项目名}/ [--phase 04_risk_report] [--verbose]
```
覆盖 AC2 覆盖度、AC4 跨文档一致性、Schema 校验、AC5 绝对表述扫描。exit 0=PASS/WARN，1=有 FAIL。

## 工具脚本（tools/）— 主要使用入口

| 脚本 | 用途 | 调用方 |
|------|------|--------|
| `consistency_checker.py` | 跨文档一致性检查（risk_id/名称/日期/金额，CONTRACT AC4） | risk-report 及下游 |
| `paddleocr_api.py` | 扫描件 PDF/图片 OCR（CONTRACT §7.2 可插拔） | 需要扫描件识别的技能 |
| `md_to_docx_enhanced.py` | Markdown→Word 增强转换（可选输出，CONTRACT §8） | 需交付 docx 的技能 |
| `risk_screener.py` | 确定性指标风险初筛卡 | dd-prep |
| `qcc_cache_manager.py` | 工商数据缓存管理（数据源无关 schema） | qcc-scan |
| `ic_version_consistency_check.py` | 投委会版一致性自检 | report-review |
| `entity_extractor.py` | NER 实体提取（零损失验收 AC1 辅助） | dd-interview（可选） |
| `doc_preprocessor.py` | 大文件文本预处理 | 通用 |
| `release_scan.py` | 发布前匿名化与凭据扫描（SECURITY.md） | 维护者/CI |
| `ima_kb_query.py` / `ima_kb_archive.py` | 第二信源适配器示例（CONTRACT §7.3，可选；导入类操作须 `--allow-external-send`） | 可选增强 |

> 已在开源重构中移除：`risk_clause_mapper.py`（关键词规则引擎，强模型直接走决策树）、`legal_ledger_generator.py`（台账由模型按 schema 直接生成）、`analysis_checker.py`（数量校验防数量不防质量）。

## 编排器（orchestrators/）

| 脚本 | 用途 |
|------|------|
| `qcc_batch_scan.py` | 工商数据批量采集编排（适配器实现） |

## 基座层（infra/）

| 模块 | 用途 |
|------|------|
| `api_client.py` | HTTP 请求统一封装（重试/超时/SSL） |
| `browser_session.py` | Playwright 浏览器启动/代理检测/session 持久化 |

## 原子能力（capabilities/）

| 模块 | 用途 |
|------|------|
| `doc_parse.py` | 文档解析（DOCX/PDF→结构化文本） |
| `ima_archive.py` | 第二信源归档（适配器示例） |
| `text_filter.py` | 文本过滤/清洗 |

## 文档引擎（docx_engine/）

Markdown→Word 转换专用引擎，8 个子模块。通过 `md_to_docx_enhanced.py` 统一调用，Skill 不直接引用。
