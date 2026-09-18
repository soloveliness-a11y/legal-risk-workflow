# 依赖分层说明

| 文件 | 内容 | 何时安装 |
|------|------|---------|
| `core.txt` | python-docx、pyyaml | 核心工作流（含报告 .docx 输出）必需 |
| `parse.txt` | markitdown[docx] | 文档解析增强（可选） |
| `browser.txt` | playwright | 第二信源浏览器脚本（可选，装后另需 `playwright install`） |
| `dev.txt` | pytest、pyyaml | 运行测试套件与本地开发 |

安装：`python3 -m pip install -r requirements/core.txt`
全量：`python3 -m pip install -r requirements/core.txt -r requirements/parse.txt -r requirements/browser.txt -r requirements/dev.txt`

外部服务适配器（工商数据源 CLI / OCR / 第二信源）不属于 Python 依赖，见 README 与 CONTRACT §7。
