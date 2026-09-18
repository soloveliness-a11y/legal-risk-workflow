"""
文本筛选原子能力

职责：
  - 将文本按章节拆分
  - 根据法律风险关键词筛选相关章节
  - 去噪（跳过免责声明、目录等通用章节）
  - 估算文本等效页数

不依赖：doc_parse（纯筛选，无解析逻辑）
"""

import re
from datetime import datetime

# 法律风险相关关键词
LEGAL_RISK_KEYWORDS = [
    '股权', '股东', '出资', '代持', '质押', '冻结', '查封',
    '诉讼', '仲裁', '行政处罚', '纠纷', '争议', '执行',
    '合同', '协议', '担保', '保证', '抵押', '质押',
    '知识产权', '专利', '商标', '著作权', '职务发明', '商业秘密',
    '关联交易', '同业竞争', '利益输送', '资金占用',
    '劳动', '社保', '公积金', '竞业', '保密', '派遣',
    '税务', '欠税', '税收优惠', '财政补贴', '偷税',
    '环保', '安全生产', '排污', '危废', '环评',
    '数据', '隐私', '算法', '出境', '备案', '个人信息',
    '贿赂', '反腐', '商业贿赂', '推广', 'CSO',
    '对赌', '回购', '优先清算', '反稀释', '一票否决',
    '国资', '外资', 'VIE', '负面清单', '安全审查',
    '合规', '牌照', '许可证', '资质', '审批',
]

# 噪音章节（通常不需要的通用性内容）
NOISE_HEADERS = [
    '免责声明', '声明', '前言', '目录', '附录',
    '索引', '术语表', '缩略语',
]


def split_into_sections(text):
    """将文本按章节标题拆分"""
    patterns = [
        r'^[一二三四五六七八九十]+[、．.]\s*.+',
        r'^\d+[\.．]\s*\S+.+',
        r'^\d+\.\d+\s*.+',
        r'^第[一二三四五六七八九十\d]+[章部分节]\s*.+',
        r'^[（(]\d+[)）]\s*.+',
        r'^#{1,4}\s+.+',
    ]

    sections = []
    current_header = "（开头部分）"
    current_lines = []

    for line in text.split('\n'):
        is_header = False
        for pattern in patterns:
            if re.match(pattern, line.strip()):
                if current_lines:
                    sections.append((current_header, '\n'.join(current_lines)))
                current_header = line.strip()
                current_lines = []
                is_header = True
                break
        if not is_header:
            current_lines.append(line)

    if current_lines:
        sections.append((current_header, '\n'.join(current_lines)))

    return sections


def filter_legal_risk_sections(sections):
    """筛选与法律风险相关的章节"""
    relevant = []
    for header, content in sections:
        is_noise = any(noise in header for noise in NOISE_HEADERS)
        if is_noise and not any(kw in content for kw in LEGAL_RISK_KEYWORDS):
            continue

        header_match = any(kw in header for kw in LEGAL_RISK_KEYWORDS)
        content_match = any(kw in content for kw in LEGAL_RISK_KEYWORDS)

        if header_match or content_match:
            relevant.append((header, content))

    return relevant


def count_approx_pages(text):
    """估算文本等效页数（按每页约800字计算）"""
    char_count = len(text.replace('\n', '').replace(' ', ''))
    return max(1, char_count // 800)


def generate_extraction_report(file_path, mode, original_pages, output_pages, extracted_headers, output_text):
    """生成精简提取报告（Markdown格式）"""
    reduction = (1 - output_pages / original_pages) * 100 if original_pages > 0 else 0
    lines = [
        f"# {__import__('os').path.basename(file_path)} - 精简提取\n",
        f"> 原文件：{file_path}",
        f"> 提取模式：{mode}",
        f"> 提取时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 原文页数：~{original_pages}页 → 精简为约{output_pages}页等效内容\n",
        "## 提取的章节",
    ]
    for h in extracted_headers:
        lines.append(f"- {h}")
    lines.extend(["\n---\n", "## 正文内容\n", output_text])
    return '\n'.join(lines), reduction
