"""
OXML 底层工具模块

职责：
  - 段落缩进设置（首行缩进、悬挂缩进）
  - 单元格边框、底纹、内边距
  - 列表符号样式
  - 页面页脚字段（PAGE / NUMPAGES）

依赖：python-docx
"""

from docx.oxml.ns import qn
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls


def set_first_line_indent_chars(para, chars):
    """设置首行缩进（字符数），使用 w:ind firstLineChars 属性。

    这是 Word 原生支持的精确字符缩进方式，比 twips 值更准确，
    因为它会根据实际字号自动换算。
    """
    pPr = para._element.get_or_add_pPr()
    existing_ind = pPr.find(qn('w:ind'))
    if existing_ind is not None:
        existing_ind.set(qn('w:firstLineChars'), str(chars * 100))
        existing_ind.set(qn('w:firstLine'), str(chars * 280))
    else:
        ind = OxmlElement('w:ind')
        ind.set(qn('w:firstLineChars'), str(chars * 100))
        ind.set(qn('w:firstLine'), str(chars * 280))
        pPr.append(ind)


def set_hanging_indent_chars(para, left_chars, hanging_chars):
    """设置左侧缩进+悬挂缩进（字符数）。

    用于无序列表项：· 符号在 left_chars - hanging_chars 位置，
    正文折行从 left_chars 位置开始。
    """
    pPr = para._element.get_or_add_pPr()
    existing_ind = pPr.find(qn('w:ind'))
    if existing_ind is not None:
        existing_ind.set(qn('w:leftChars'), str(int(left_chars * 100)))
        existing_ind.set(qn('w:left'), str(int(left_chars * 280)))
        existing_ind.set(qn('w:hangingChars'), str(int(hanging_chars * 100)))
        existing_ind.set(qn('w:hanging'), str(int(hanging_chars * 280)))
        for attr in [qn('w:firstLine'), qn('w:firstLineChars')]:
            if attr in existing_ind.attrib:
                del existing_ind.attrib[attr]
    else:
        ind = OxmlElement('w:ind')
        ind.set(qn('w:leftChars'), str(int(left_chars * 100)))
        ind.set(qn('w:left'), str(int(left_chars * 280)))
        ind.set(qn('w:hangingChars'), str(int(hanging_chars * 100)))
        ind.set(qn('w:hanging'), str(int(hanging_chars * 280)))
        pPr.append(ind)


def add_list_bullet_style(para):
    """给段落添加 Word 内置项目符号（Bullet Character）样式。

    使用 Word 内置的 w:abstractNumId=1（Bullet Char 编号定义），
    通过 numPr 元素让段落显示原生项目符号，比手写 "· " 更整齐。
    """
    pPr = para._element.get_or_add_pPr()
    numPr = OxmlElement('w:numPr')
    ilvl = OxmlElement('w:ilvl')
    ilvl.set(qn('w:val'), '0')
    numId = OxmlElement('w:numId')
    numId.set(qn('w:val'), '1')
    numPr.append(ilvl)
    numPr.append(numId)
    pPr.append(numPr)


def set_outline_level(para, level):
    """为段落设置大纲级别（0-based，level 1→0, level 2→1, level 3→2）

    使标题出现在 Word 导航窗格中，支持生成目录。
    """
    if level > 3:
        return
    pPr = para._element.get_or_add_pPr()
    outlineLvl = OxmlElement('w:outlineLvl')
    outlineLvl.set(qn('w:val'), str(level - 1))
    pPr.append(outlineLvl)


def set_cell_border(cell, **kwargs):
    """设置单元格边框"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('start', 'top', 'end', 'bottom', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            element = OxmlElement(f'w:{edge}')
            for key, attr_val in edge_data.items():
                element.set(qn(f'w:{key}'), str(attr_val))
            tcBorders.append(element)
    tcPr.append(tcBorders)


def set_cell_shading(cell, color_hex):
    """设置单元格底纹颜色"""
    shading_elm = parse_xml(
        f'<w:shd {nsdecls("w")} w:fill="{color_hex}" w:val="clear"/>'
    )
    cell._tc.get_or_add_tcPr().append(shading_elm)


def set_cell_margins(cell, top=60, bottom=60, left=100, right=100):
    """设置单元格内边距（单位：twips，1pt = 20twips）"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for edge, val in [('top', top), ('bottom', bottom), ('start', left), ('end', right)]:
        elem = OxmlElement(f'w:{edge}')
        elem.set(qn('w:w'), str(val))
        elem.set(qn('w:type'), 'dxa')
        tcMar.append(elem)
    tcPr.append(tcMar)


def add_page_field(para, field_type='PAGE'):
    """在段落中添加 Word 字段（PAGE 或 NUMPAGES）。

    返回添加字段所用的 run 对象（便于外层继续添加文本）。
    """
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    run_page = para.add_run()
    run_page._element.append(fldChar1)

    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = f' {field_type} '
    run_instr = para.add_run()
    run_instr._element.append(instrText)

    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    run_end = para.add_run()
    run_end._element.append(fldChar2)
    return run_end


def add_page_break_element(run):
    """在 run 中添加分页符"""
    br = OxmlElement('w:br')
    br.set(qn('w:type'), 'page')
    run._element.append(br)
