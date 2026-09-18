"""
文本处理模块（纯文本操作，不依赖 python-docx）

职责：
  - YAML frontmatter 剥离
  - 中英文标点转换
  - Markdown 行内格式解析（**加粗** / *斜体*）
"""

from .constants import PUNCTUATION_MAP, PUNCTUATION_RESTORE_PATTERNS


def convert_punctuation(text):
    """将文本中的英文标点转换为中文标点。

    实现逻辑（基于 IBD Tools by SyH Word宏）：
    1. 逐字符扫描，将英文标点替换为对应中文标点
    2. 双引号按出现顺序奇偶配对：奇数次→左引号"，偶数次→右引号"
    3. 最后恢复数字间的半角标点（避免 1,000 → 1，000）

    重要：此函数仅应用于已从Markdown中提取的纯文本，不可用于
    未解析的Markdown源文本，否则会破坏语法字符（-/. >/---等）。
    """
    if not text:
        return text

    result = []
    quote_count = 0

    for char in text:
        if char == '"':
            quote_count += 1
            if quote_count % 2 == 1:
                result.append('\u201c')
            else:
                result.append('\u201d')
        elif char in PUNCTUATION_MAP:
            result.append(PUNCTUATION_MAP[char])
        else:
            result.append(char)

    converted = ''.join(result)

    for pattern, replacement in PUNCTUATION_RESTORE_PATTERNS:
        while True:
            new_converted = pattern.sub(replacement, converted)
            if new_converted == converted:
                break
            converted = new_converted

    # 中文标点后去除多余空格（如 **风控提示：** 文本 → "风控提示： 文本" → "风控提示：文本"）
    import re as _re
    converted = _re.sub(r'([：；，。！？）】》])\s+', r'\1', converted)

    return converted


def strip_frontmatter(content):
    """剥离 YAML frontmatter，返回 (metadata_dict, body_content)"""
    metadata = {}
    if content.startswith('---'):
        end = content.find('---', 3)
        if end != -1:
            yaml_text = content[3:end].strip()
            body = content[end + 3:].lstrip('\n')
            for line in yaml_text.split('\n'):
                if ':' in line:
                    key, _, val = line.partition(':')
                    metadata[key.strip()] = val.strip().strip('"').strip("'")
            return metadata, body
    return metadata, content


def parse_inline_formats(text):
    """解析行内格式（加粗、斜体），返回 (text, is_bold, is_italic) 列表"""
    import re as _re
    segments = []
    parts = _re.split(r'(\*\*.*?\*\*|\*.*?\*)', text)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            segments.append((part[2:-2], True, False))
        elif part.startswith('*') and part.endswith('*') and not part.startswith('**'):
            segments.append((part[1:-1], False, True))
        else:
            segments.append((part, False, False))

    # 清理：加粗段末尾是中文标点时，去掉下一段开头的空格
    # 解决 **风控提示：** 后文 → segments间残留空格的问题
    _cn_punct = set('：；，。！？）】》')
    for i in range(len(segments) - 1):
        cur_text, cur_bold, cur_italic = segments[i]
        if cur_bold and cur_text and cur_text[-1] in _cn_punct:
            next_text, next_bold, next_italic = segments[i + 1]
            if next_text and next_text[0] == ' ':
                segments[i + 1] = (next_text.lstrip(' '), next_bold, next_italic)

    return segments
