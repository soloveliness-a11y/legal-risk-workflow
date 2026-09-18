"""
CLI 入口模块

职责：命令行参数解析与分发。
保持与原 md_to_docx_enhanced.py 完全一致的 CLI 接口。
"""

import argparse
import os
import sys

from .converter import convert_single_file, convert_merge_files


def main():
    parser = argparse.ArgumentParser(
        description='增强版 Markdown → Word 转换 V4（原子能力引擎）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模式说明：
  normal      (默认) 标准转换
  enhanced    增强模式，渲染风险标记颜色
  risk_report 风控报告模式，匹配投委会版本格式（楷体14pt，固定行距，首行缩进2字符）

V4 架构：
  基于 docx_engine 原子能力包重构，功能与 V3.2 完全一致，
  内部按 constants / text_utils / oxml_utils / docx_base /
  paragraph_renderer / table_renderer / converter / cli 拆分。

示例：
  python3 -m docx_engine.cli --input report.md --output report.docx --mode risk_report
  python3 -m docx_engine.cli --input result.md --output report.docx --mode enhanced
  python3 -m docx_engine.cli --merge --inputs "part1.md,part2.md" --output full.docx --mode enhanced
        """
    )

    parser.add_argument('--input', default=None, help='输入 Markdown 文件路径（单文件模式）')
    parser.add_argument('--output', required=True, help='输出 Word 文件路径')
    parser.add_argument('--title', default=None, help='文档标题（生成封面）')
    parser.add_argument('--subtitle', default=None, help='封面副标题')
    parser.add_argument('--date', default=None, help='封面日期（如 "2026年4月8日"）')
    parser.add_argument('--header', default=None, help='页眉文字')
    parser.add_argument('--mode', choices=['normal', 'enhanced', 'risk_report'], default='normal',
                        help='转换模式: normal(标准)|enhanced(风险标记渲染)|risk_report(风控报告格式)')

    parser.add_argument('--merge', action='store_true', help='启用合并模式（多文件合并为一个 docx）')
    parser.add_argument('--inputs', default=None, help='合并模式的输入文件列表，逗号分隔')

    args = parser.parse_args()

    if args.merge:
        if not args.inputs:
            print("Error: --merge requires --inputs parameter")
            sys.exit(1)
        input_paths = [p.strip() for p in args.inputs.split(',')]
        for p in input_paths:
            if not os.path.exists(p):
                print(f"Error: Input file not found: {p}")
                sys.exit(1)
        convert_merge_files(input_paths, args.output, args.title, args.mode,
                            args.subtitle, args.date, args.header)
    else:
        if not args.input:
            print("Error: --input is required (or use --merge --inputs)")
            sys.exit(1)
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}")
            sys.exit(1)
        convert_single_file(args.input, args.output, args.title, args.mode,
                            args.subtitle, args.date, args.header)


if __name__ == '__main__':
    main()
