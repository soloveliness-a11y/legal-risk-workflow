"""
常量与样式配置模块

存放所有不依赖外部库的全局常量、样式字典、正则表达式。
支持从 config.yaml 加载覆盖默认值。
"""

import os
import re
import sys

# ── 加载集中配置 ──
_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

try:
    from config_loader import get_config
    _cfg = get_config()
except ImportError:
    _cfg = None

def _cfg_val(key, default):
    """从 config.yaml 获取值，不可用时返回默认值"""
    if _cfg is None:
        return default
    return _cfg.get(key, default)

# ── 通用阈值 ──────────────────────────────────────────────────────

# 大文件阈值（字符数）
LARGE_FILE_THRESHOLD = 10000

# ── 风险标记颜色映射 ──────────────────────────────────────────────

try:
    from docx.shared import RGBColor
    RISK_COLORS = {
        "高": RGBColor(0xCC, 0x00, 0x00),
        "🔴": RGBColor(0xCC, 0x00, 0x00),
        "中高": RGBColor(0xE6, 0x7E, 0x00),
        "中": RGBColor(0xE6, 0x7E, 0x00),
        "🟡": RGBColor(0xE6, 0x7E, 0x00),
        "中低": RGBColor(0x00, 0x80, 0x00),
        "低": RGBColor(0x00, 0x80, 0x00),
        "🟢": RGBColor(0x00, 0x80, 0x00),
    }
except ImportError:
    RISK_COLORS = {}

# 风险标记正则：仅在段落开头匹配，且后跟边界字符
RISK_PREFIX_PATTERN = re.compile(
    r'^(🔴|🟡|🟢|中高|中低|高|中|低)(?:风险|：|:|级|\s|$)'
)

# ── 中英文标点转换 ──────────────────────────────────────────────

# 英文标点 → 中文标点映射（不含双引号，双引号单独处理）
PUNCTUATION_MAP = {
    ',': '，',
    '.': '。',
    ';': '；',
    ':': '：',
    '?': '？',
    '!': '！',
    '-': '—',
    '~': '～',
    '(': '（',
    ')': '）',
    '<': '《',
    '>': '》',
}

# 需要保留半角标点的场景：数字之间的逗号、句号、破折号
PUNCTUATION_RESTORE_PATTERNS = [
    (re.compile(r'([0-9])[，]([0-9])'), r'\1,\2'),
    (re.compile(r'([0-9])[。]([0-9])'), r'\1.\2'),
    (re.compile(r'([0-9])[。]([A-Za-z])'), r'\1.\2'),
    (re.compile(r'(\d{1,2})[。]\s*([\u4e00-\u9fff])'), r'\1. \2'),
    (re.compile(r'([A-Z])[。]\s*([\u4e00-\u9fff])'), r'\1. \2'),
    (re.compile(r'([A-Z])[。]\s*([A-Za-z])'), r'\1. \2'),
    (re.compile(r'[—]([0-9])'), r'-\1'),
    (re.compile(r'[—]([A-Za-z])'), r'-\1'),  # Pre-A, A-B等英文间连字符
    (re.compile(r'([A-Za-z])[—]([A-Za-z])'), r'\1-\2'),  # 英文间连字符双保险
]

# ── 标题层级样式配置（默认模式）───────────────────────────────────

try:
    from docx.shared import RGBColor as _RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH as _WD_ALIGN_PARAGRAPH

    HEADING_STYLES = {
        0: {"font_cn": "黑体", "font_en": "Arial", "size": 22, "bold": True,
            "space_before": 0, "space_after": 12, "alignment": _WD_ALIGN_PARAGRAPH.CENTER},
        1: {"font_cn": "黑体", "font_en": "Arial", "size": 16, "bold": True,
            "space_before": 24, "space_after": 12, "color": _RGBColor(0x1A, 0x1A, 0x2E)},
        2: {"font_cn": "黑体", "font_en": "Arial", "size": 14, "bold": True,
            "space_before": 18, "space_after": 8, "color": _RGBColor(0x2C, 0x3E, 0x50)},
        3: {"font_cn": "黑体", "font_en": "Arial", "size": 12, "bold": True,
            "space_before": 12, "space_after": 6, "color": _RGBColor(0x34, 0x49, 0x5E)},
        4: {"font_cn": "宋体", "font_en": "Times New Roman", "size": 11, "bold": True,
            "space_before": 8, "space_after": 4, "color": _RGBColor(0x34, 0x49, 0x5E)},
    }
except ImportError:
    HEADING_STYLES = {}

# ── 表格配色（默认模式）───────────────────────────────────────────

TABLE_HEADER_BG = "D6E4F0"   # 浅蓝
TABLE_ALT_ROW_BG = "F5F5F5"  # 浅灰

# ── 风控报告专用样式 ──────────────────────────────────────────────

RISK_REPORT_STYLE = {
    "page_size": _cfg_val("docx.report_style.page_size", "A4"),
    "margin_top": _cfg_val("docx.report_style.margin_top", 2.80),
    "margin_bottom": _cfg_val("docx.report_style.margin_bottom", 2.80),
    "margin_left": _cfg_val("docx.report_style.margin_left", 2.54),
    "margin_right": _cfg_val("docx.report_style.margin_right", 2.54),
    "font_cn": _cfg_val("docx.report_style.font_cn", "楷体"),
    "font_en": _cfg_val("docx.report_style.font_en", "Times New Roman"),
    "font_size_pt": _cfg_val("docx.report_style.font_size_pt", 12),
    "first_line_indent_chars": _cfg_val("docx.report_style.first_line_indent_chars", 2),
    "line_spacing_pt": _cfg_val("docx.report_style.line_spacing_pt", 28),
    "alignment": "justify",
    "cover_title_size_pt": _cfg_val("docx.report_style.cover_title_size_pt", 14),
    "cover_subtitle_size_pt": _cfg_val("docx.report_style.cover_subtitle_size_pt", 12),
    "cover_meta_size_pt": _cfg_val("docx.report_style.cover_meta_size_pt", 12),
    "h1_size_pt": _cfg_val("docx.report_style.h1_size_pt", 12),
    "table_font_size_pt": _cfg_val("docx.report_style.table_font_size_pt", 10.5),
    "table_line_spacing": _cfg_val("docx.report_style.table_line_spacing", 1.0),
    "table_header_bold": _cfg_val("docx.report_style.table_header_bold", True),
}
