"""
核心转换器模块

职责：
  - Markdown 内容 → docx 元素的完整转换流水线
  - 封面预处理（risk_report 模式）
  - 落款检测与处理
  - 单文件转换 / 多文件合并

依赖：python-docx, 所有 docx_engine 子模块
"""

import os
import re

from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .constants import RISK_REPORT_STYLE, LARGE_FILE_THRESHOLD
from .text_utils import convert_punctuation
from .docx_base import add_heading, add_page_break, add_horizontal_rule, create_document
from .paragraph_renderer import add_paragraph, add_list_item, add_run_with_format
from .table_renderer import parse_markdown_table, add_table


def convert_md_content_to_docx(doc, content, mode="normal"):
    """将 Markdown 内容转换为 docx 元素（追加到现有 doc）"""
    from .text_utils import strip_frontmatter
    metadata, body = strip_frontmatter(content)

    lines = body.split('\n')
    i = 0
    table_buffer = []
    cover_end_idx = None

    # ── 风控报告模式：封面预处理 ──
    cover_done = False
    if mode == "risk_report":
        for ci, cl in enumerate(lines):
            cs = cl.strip()
            if cs == '各位投委会委员：' or cs.startswith('各位投委会委员'):
                cover_end_idx = ci
                break

        if cover_end_idx is not None:
            company_name = None
            report_title = None
            meta_parts = []

            for ci in range(cover_end_idx):
                cs = lines[ci].strip()
                if not cs or cs == '---':
                    continue
                if cs.startswith('# ') and not cs.startswith('## '):
                    company_name = cs.lstrip('#').strip()
                elif cs.startswith('## '):
                    report_title = cs.lstrip('#').strip()
                elif cs.startswith('**') and cs.endswith('**'):
                    inner = cs[2:-2]
                    if '：' in inner:
                        _, val = inner.split('：', 1)
                        meta_parts.append(val.strip())
                    elif ':' in inner:
                        _, val = inner.split(':', 1)
                        meta_parts.append(val.strip())
                    else:
                        meta_parts.append(inner)

            if company_name:
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = Pt(RISK_REPORT_STYLE["line_spacing_pt"])
                run = para.add_run(convert_punctuation(company_name))
                run.bold = True
                from .paragraph_renderer import set_run_font
                set_run_font(run, RISK_REPORT_STYLE["font_en"], RISK_REPORT_STYLE["font_cn"],
                             RISK_REPORT_STYLE["cover_title_size_pt"])

            if report_title:
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = Pt(RISK_REPORT_STYLE["line_spacing_pt"])
                run = para.add_run(convert_punctuation(report_title))
                run.bold = True
                set_run_font(run, RISK_REPORT_STYLE["font_en"], RISK_REPORT_STYLE["font_cn"],
                             RISK_REPORT_STYLE["cover_subtitle_size_pt"])

            if meta_parts:
                meta_line = convert_punctuation('；'.join(meta_parts))
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = Pt(RISK_REPORT_STYLE["line_spacing_pt"])
                run = para.add_run(meta_line)
                run.bold = False
                set_run_font(run, RISK_REPORT_STYLE["font_en"], RISK_REPORT_STYLE["font_cn"],
                             RISK_REPORT_STYLE["cover_meta_size_pt"])

            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            para.paragraph_format.space_before = Pt(0)
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = Pt(RISK_REPORT_STYLE["line_spacing_pt"])
            run = para.add_run('各位投委会委员：')
            run.bold = True
            set_run_font(run, RISK_REPORT_STYLE["font_en"], RISK_REPORT_STYLE["font_cn"],
                         RISK_REPORT_STYLE["font_size_pt"])

            cover_done = True
            i = cover_end_idx + 1

    # ── 风控报告落款检测 ──
    signature_idx = None
    if mode == "risk_report":
        for si in range(len(lines) - 1, max(len(lines) - 20, 0), -1):
            sl = lines[si].strip()
            if sl == '风险控制部' or sl == '风险控制部（风控部）':
                signature_idx = si
                break

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if cover_done and cover_end_idx is not None and i <= cover_end_idx:
            i += 1
            continue

        if stripped.lower().startswith('<!-- pagebreak') or stripped.lower().startswith('<!--pagebreak'):
            add_page_break(doc)
            i += 1
            continue

        # 表格
        if stripped.startswith('|'):
            table_buffer.append(stripped)
            i += 1
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_buffer.append(lines[i].strip())
                i += 1
            rows = parse_markdown_table(table_buffer)
            if rows:
                header = rows[0]
                data = rows[1:]
                add_table(doc, header, data, mode)
            table_buffer = []
            continue

        # 标题
        if stripped.startswith('#'):
            level = len(stripped) - len(stripped.lstrip('#'))
            if mode == "risk_report" and cover_done and level <= 2:
                if cover_end_idx is not None and i <= cover_end_idx:
                    i += 1
                    continue
            add_heading(doc, stripped, level, mode)

            # risk_report模式：H1标题后紧跟的括号行视为副标题（居中、无缩进）
            if mode == "risk_report" and level == 1:
                peek = i + 1
                while peek < len(lines) and not lines[peek].strip():
                    peek += 1
                if peek < len(lines):
                    next_stripped = lines[peek].strip()
                    if next_stripped.startswith('（') and next_stripped.endswith('）'):
                        sub_para = doc.add_paragraph()
                        sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        sub_para.paragraph_format.space_before = Pt(0)
                        sub_para.paragraph_format.space_after = Pt(6)
                        sub_para.paragraph_format.line_spacing = Pt(RISK_REPORT_STYLE["line_spacing_pt"])
                        sub_run = sub_para.add_run(convert_punctuation(next_stripped))
                        sub_run.bold = False
                        from .paragraph_renderer import set_run_font
                        set_run_font(sub_run, RISK_REPORT_STYLE["font_en"],
                                     RISK_REPORT_STYLE["font_cn"],
                                     RISK_REPORT_STYLE["cover_subtitle_size_pt"])
                        i = peek  # skip to the company name line
            i += 1
            continue

        # 分隔线
        if stripped == '---':
            if mode == "risk_report":
                spacer = doc.add_paragraph()
                spacer.paragraph_format.space_before = Pt(0)
                spacer.paragraph_format.space_after = Pt(0)
                spacer.paragraph_format.line_spacing = Pt(6)
            else:
                add_horizontal_rule(doc)
            i += 1
            continue

        # 落款：从"风险控制部"开始，到日期行结束，所有行右对齐
        if mode == "risk_report" and signature_idx is not None and i == signature_idx:
            sig_lines = []
            j = signature_idx
            import re as _re
            date_pattern = _re.compile(r'\d{4}年\d{1,2}月\d{1,2}日')
            while j < len(lines):
                sl = lines[j].strip()
                if not sl:
                    j += 1
                    continue
                # 遇到分隔线或斜体免责声明 → 结束
                if sl == '---' or (sl.startswith('*') and sl.endswith('*') and not sl.startswith('**')):
                    break
                sig_lines.append(sl)
                j += 1
                # 日期行是落款区最后一行
                if date_pattern.search(sl):
                    break

            for sig_text in sig_lines:
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = Pt(RISK_REPORT_STYLE["line_spacing_pt"])
                run = para.add_run(convert_punctuation(sig_text))
                from .paragraph_renderer import set_run_font
                set_run_font(run, RISK_REPORT_STYLE["font_en"], RISK_REPORT_STYLE["font_cn"],
                             RISK_REPORT_STYLE["font_size_pt"])

            i = j
            continue

        # 无序列表
        if stripped.startswith(('- ', '* ', '\u2022 ')):
            text = stripped[2:].strip()
            add_list_item(doc, text, ordered=False, mode=mode)
            i += 1
            continue

        # 有序列表
        if re.match(r'^\d+[\.\)\u3001](?!\d)\s*', stripped):
            num_match = re.match(r'^(\d+[\.\)\u3001])', stripped)
            number_text = num_match.group(1) if num_match else None
            text = re.sub(r'^\d+[\.\)\u3001]\s*', '', stripped)
            is_new_list = num_match and num_match.group(1).rstrip('.\uff0e)\u3001') == '1'
            add_list_item(doc, text, ordered=True, number_text=number_text,
                          mode=mode, is_new_list=is_new_list)
            i += 1
            continue

        # 引用
        if stripped.startswith('>'):
            text = stripped.lstrip('>').strip()
            if mode == "risk_report":
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                para.paragraph_format.line_spacing = Pt(RISK_REPORT_STYLE["line_spacing_pt"])
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.space_after = Pt(0)
                from .oxml_utils import set_first_line_indent_chars
                set_first_line_indent_chars(para, RISK_REPORT_STYLE["first_line_indent_chars"])
                from .text_utils import parse_inline_formats
                segments = parse_inline_formats(text)
                for seg_text, is_bold, is_italic in segments:
                    if not seg_text:
                        continue
                    add_run_with_format(para, seg_text, is_bold, is_italic, mode=mode)
            else:
                para = doc.add_paragraph(convert_punctuation(text), style='Quote')
                para.paragraph_format.space_before = Pt(3)
                para.paragraph_format.space_after = Pt(3)
            i += 1
            continue

        # 普通段落
        add_paragraph(doc, stripped, mode)
        i += 1


def convert_single_file(input_path, output_path, title=None, mode="normal",
                         subtitle=None, date_str=None, header_text=None):
    """转换单个文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    doc = create_document(title=title, subtitle=subtitle, date_str=date_str,
                           header_text=header_text, mode=mode)

    if len(content) > LARGE_FILE_THRESHOLD:
        print(f"[安全模式] 输入文件较大 ({len(content)} 字符)，自动启用分段处理")

    convert_md_content_to_docx(doc, content, mode)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    doc.save(output_path)
    print(f"Word document saved: {output_path}")


def convert_merge_files(input_paths, output_path, title=None, mode="normal",
                         subtitle=None, date_str=None, header_text=None):
    """合并多个 Markdown 文件为一个 Word 文档"""
    doc = create_document(title=title, subtitle=subtitle, date_str=date_str,
                           header_text=header_text, mode=mode)

    for idx, input_path in enumerate(input_paths):
        path = input_path.strip()
        if not os.path.exists(path):
            print(f"Warning: File not found, skipping: {path}")
            continue

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if len(content) > LARGE_FILE_THRESHOLD:
            print(f"[安全模式] {os.path.basename(path)} 较大 ({len(content)} 字符)，自动启用分段处理")

        if idx > 0:
            add_page_break(doc)

        convert_md_content_to_docx(doc, content, mode)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    doc.save(output_path)
    print(f"Merged Word document saved: {output_path} ({len(input_paths)} files)")
