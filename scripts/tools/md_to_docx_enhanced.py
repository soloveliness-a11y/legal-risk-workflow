#!/usr/bin/env python3
"""
增强版 Markdown → Word 转换脚本 V4.0（兼容入口）

⚠️  本文件现为兼容层，内部逻辑已全部迁移至 docx_engine/ 原子能力包。
    直接调用本文件仍可正常工作，但新开发建议引用 docx_engine 模块。

迁移说明：
  - V3.2 的 1625 行单体代码 → 拆分为 8 个原子模块
  - 功能 100% 保留，CLI 接口 100% 兼容
  - 新增 Python API：from docx_engine.converter import convert_single_file

原子能力包结构（scripts/docx_engine/）：
  constants.py          → 常量、样式配置、风险颜色
  text_utils.py         → 标点转换、frontmatter剥离、行内格式解析
  oxml_utils.py         → OXML底层操作（缩进、边框、底纹、字段）
  docx_base.py          → 文档创建、页眉页脚、封面、标题
  paragraph_renderer.py → 段落渲染、列表项、run字体
  table_renderer.py     → 表格解析、列宽计算、表格渲染
  converter.py          → 核心转换流水线（封面/落款/正文）
  cli.py                → 命令行入口
"""

import sys
import os

# 将 scripts/ 加入路径，确保 docx_engine 可被导入
_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from docx_engine.cli import main

if __name__ == '__main__':
    main()
