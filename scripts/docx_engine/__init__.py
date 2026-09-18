"""
Docx Engine - Markdown to Word 转换引擎（原子能力包）

从 md_to_docx_enhanced.py V3.2 拆分而来。
按功能维度拆分为最小原子模块，支持三种渲染模式：
  - normal:    标准转换
  - enhanced:  风险标记渲染
  - risk_report: 风控报告格式（楷体14pt/固定行距28pt/首行缩进2字符）

用法（兼容原 CLI）：
  python3 -m docx_engine.cli --input report.md --output report.docx --mode risk_report

用法（Python API）：
  from docx_engine.converter import convert_single_file
  convert_single_file("report.md", "report.docx", mode="risk_report")
"""

__version__ = "4.0.0"
__all__ = [
    "convert_single_file",
    "convert_merge_files",
    "convert_md_content_to_docx",
]

from .converter import convert_single_file, convert_merge_files, convert_md_content_to_docx
