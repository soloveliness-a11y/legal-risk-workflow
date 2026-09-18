"""
文档基础操作模块

职责：
  - 创建 Document 对象并设置默认样式（三种模式）
  - 添加页眉、页脚、封面标题
  - 添加水平分隔线、分页符
  - 添加标题（带层级样式 + 大纲级别）

依赖：python-docx, constants, oxml_utils, text_utils
"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from .constants import HEADING_STYLES, RISK_REPORT_STYLE
from .oxml_utils import set_outline_level
from .text_utils import convert_punctuation


def create_document(title=None, subtitle=None, date_str=None, header_text=None, mode="normal"):
    """创建文档并设置默认样式、页眉页脚"""
    doc = Document()

    if mode == "risk_report":
        style = doc.styles['Normal']
        font = style.font
        font.name = RISK_REPORT_STYLE["font_en"]
        font.size = Pt(RISK_REPORT_STYLE["font_size_pt"])
        style.element.rPr.rFonts.set(qn('w:eastAsia'), RISK_REPORT_STYLE["font_cn"])

        para_fmt = style.paragraph_format
        para_fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para_fmt.space_before = Pt(0)
        para_fmt.space_after = Pt(0)
        para_fmt.line_spacing = Pt(28)

        for section in doc.sections:
            section.page_width = Cm(21.0)
            section.page_height = Cm(29.7)
            section.top_margin = Cm(RISK_REPORT_STYLE["margin_top"])
            section.bottom_margin = Cm(RISK_REPORT_STYLE["margin_bottom"])
            section.left_margin = Cm(RISK_REPORT_STYLE["margin_left"])
            section.right_margin = Cm(RISK_REPORT_STYLE["margin_right"])

        return doc

    # 默认模式
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    para_fmt = style.paragraph_format
    para_fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    para_fmt.space_before = Pt(3)
    para_fmt.space_after = Pt(3)
    para_fmt.line_spacing = 1.25

    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.18)
        section.right_margin = Cm(3.18)

    add_page_footer(doc)
    add_page_header(doc, header_text)

    if title:
        add_cover_title(doc, title, subtitle, date_str)

    return doc


def add_page_footer(doc):
    """添加页脚页码：第 X 页 / 共 Y 页"""
    from .oxml_utils import add_page_field
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(0)

        run1 = para.add_run("— ")
        run1.font.size = Pt(9)
        run1.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        add_page_field(para, 'PAGE')

        run2 = para.add_run(" / ")
        run2.font.size = Pt(9)
        run2.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        add_page_field(para, 'NUMPAGES')

        run3 = para.add_run(" —")
        run3.font.size = Pt(9)
        run3.font.color.rgb = RGBColor(0x99, 0x99, 0x99)


def add_page_header(doc, header_text=None):
    """添加页眉（可选文档标题）"""
    if not header_text:
        return
    for section in doc.sections:
        header = section.header
        header.is_linked_to_previous = False
        para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = para.add_run(header_text)
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
        run.font.name = '宋体'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

        pPr = para._element.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '4')
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), 'CCCCCC')
        pBdr.append(bottom)
        pPr.append(pBdr)


def add_cover_title(doc, title, subtitle=None, date_str=None):
    """添加封面标题区域"""
    for _ in range(3):
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(0)
        spacer.paragraph_format.line_spacing = 1.0

    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_para.paragraph_format.space_before = Pt(24)
    title_para.paragraph_format.space_after = Pt(6)
    title_run = title_para.add_run(title)
    title_run.bold = True
    title_run.font.size = Pt(22)
    title_run.font.name = 'Arial'
    title_run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    title_run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

    if subtitle:
        sub_para = doc.add_paragraph()
        sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_para.paragraph_format.space_before = Pt(6)
        sub_para.paragraph_format.space_after = Pt(6)
        sub_run = sub_para.add_run(subtitle)
        sub_run.font.size = Pt(14)
        sub_run.font.name = 'Times New Roman'
        sub_run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        sub_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    if date_str:
        date_para = doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_para.paragraph_format.space_before = Pt(12)
        date_para.paragraph_format.space_after = Pt(6)
        date_run = date_para.add_run(date_str)
        date_run.font.size = Pt(11)
        date_run.font.name = 'Times New Roman'
        date_run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        date_run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    add_horizontal_rule(doc)

    spacer2 = doc.add_paragraph()
    spacer2.paragraph_format.space_before = Pt(0)
    spacer2.paragraph_format.space_after = Pt(0)


def add_horizontal_rule(doc):
    """添加水平分隔线（细线，不分页）"""
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(6)
    para.paragraph_format.line_spacing = 1.0

    pPr = para._element.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'CCCCCC')
    pBdr.append(bottom)


def add_page_break(doc):
    """添加分页符"""
    from .oxml_utils import add_page_break_element
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(0)
    run = para.add_run()
    add_page_break_element(run)


def add_heading(doc, text, level, mode="normal"):
    """添加标题（带精细层级样式 + 大纲级别）"""
    text = text.lstrip('#').strip()
    text = convert_punctuation(text)

    if mode == "risk_report":
        para = doc.add_paragraph()
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(0)
        para.paragraph_format.line_spacing = Pt(RISK_REPORT_STYLE["line_spacing_pt"])

        run = para.add_run(text)
        rFonts = run._element.get_or_add_rPr().get_or_add_rFonts()
        rFonts.set(qn('w:ascii'), RISK_REPORT_STYLE["font_en"])
        rFonts.set(qn('w:hAnsi'), RISK_REPORT_STYLE["font_cn"])
        rFonts.set(qn('w:eastAsia'), RISK_REPORT_STYLE["font_cn"])
        run.bold = True

        if level == 1:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_after = Pt(6)
            run.font.size = Pt(RISK_REPORT_STYLE["cover_title_size_pt"])
        elif level == 2:
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            run.font.size = Pt(RISK_REPORT_STYLE["font_size_pt"])
        else:
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            run.font.size = Pt(RISK_REPORT_STYLE["font_size_pt"])
            from .oxml_utils import set_first_line_indent_chars
            set_first_line_indent_chars(para, RISK_REPORT_STYLE["first_line_indent_chars"])

        set_outline_level(para, level)
        return para

    # 默认模式
    config = HEADING_STYLES.get(level, HEADING_STYLES.get(4, {}))
    heading = doc.add_heading(text, level=min(level, 4))

    for run in heading.runs:
        run.font.name = config.get("font_en", "Arial")
        run._element.rPr.rFonts.set(qn('w:eastAsia'), config.get("font_cn", "黑体"))
        run.font.size = Pt(config.get("size", 12))
        run.bold = config.get("bold", True)
        if "color" in config:
            run.font.color.rgb = config["color"]

    heading.paragraph_format.space_before = Pt(config.get("space_before", 12))
    heading.paragraph_format.space_after = Pt(config.get("space_after", 6))

    if level == 0 and "alignment" in config:
        heading.alignment = config["alignment"]

    return heading
