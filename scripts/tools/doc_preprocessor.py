#!/usr/bin/env python3
"""
大文件文本预处理脚本 - V3.0（兼容入口）

⚠️  本文件现为兼容层，内部逻辑已拆分为原子能力：
    - capabilities/doc_parse.py   → 文档解析（PDF/DOCX/TXT）
    - capabilities/text_filter.py → 文本筛选（章节拆分、关键词过滤）

用法（不变）：
  python3 doc_preprocessor.py --input "文件路径" --output "输出路径" --mode legal_risk
"""

import argparse
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from capabilities.doc_parse import extract_text
from capabilities.text_filter import (
    split_into_sections, filter_legal_risk_sections,
    count_approx_pages, generate_extraction_report, NOISE_HEADERS
)


def preprocess(file_path, output_path, mode='legal_risk'):
    """主处理函数"""
    print(f"Extracting text from: {file_path}")
    text = extract_text(file_path)
    if not text:
        print("Failed to extract text. Aborting.")
        sys.exit(1)

    original_pages = count_approx_pages(text)
    print(f"Original text: ~{original_pages} pages equivalent")

    if mode == 'full_text':
        sections = split_into_sections(text)
        filtered = [(h, c) for h, c in sections
                    if not any(noise in h for noise in NOISE_HEADERS)]
    else:
        sections = split_into_sections(text)
        filtered = filter_legal_risk_sections(sections)

    extracted_headers = [h for h, _ in filtered]
    output_text = '\n\n'.join(content for _, content in filtered)
    output_pages = count_approx_pages(output_text)

    report_md, reduction = generate_extraction_report(
        file_path, mode, original_pages, output_pages, extracted_headers, output_text
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_md)

    print(f"Output: {output_path}")
    print(f"Reduced: ~{original_pages} pages → ~{output_pages} pages ({reduction:.0f}% reduction)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='大文件文本预处理 - 法律风险聚焦')
    parser.add_argument('--input', required=True, help='输入文件路径（PDF/DOCX/TXT/MD）')
    parser.add_argument('--output', required=True, help='输出文件路径（Markdown）')
    parser.add_argument('--mode', default='legal_risk',
                       choices=['legal_risk', 'full_text'],
                       help='提取模式：legal_risk(法律风险聚焦) / full_text(全文提取)')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    preprocess(args.input, args.output, args.mode)
