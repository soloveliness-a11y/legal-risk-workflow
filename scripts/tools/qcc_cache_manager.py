#!/usr/bin/env python3
"""
企查查缓存管理工具

用途：查询、比对、导出企查查缓存数据
支持 post-invest-check 定期扫描时的增量比对

使用方式：
  python3 qcc_cache_manager.py show <cache_path>                  # 显示缓存摘要
  python3 qcc_cache_manager.py diff <old_cache> <new_cache>       # 比对两个缓存的差异
  python3 qcc_cache_manager.py export <cache_path> <output_path>  # 导出为可读报告
"""

import argparse
import json
import sys
import os
from datetime import datetime


def load_cache(path):
    """加载缓存文件"""
    if not os.path.exists(path):
        print(f"Error: Cache file not found: {path}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def show_cache(cache_path):
    """显示缓存摘要"""
    data = load_cache(cache_path)
    
    print(f"项目: {data.get('project_name', 'N/A')}")
    print(f"查询日期: {data.get('query_date', 'N/A')}")
    
    # 基础信息
    basic = data.get('basic_info', {})
    if basic:
        print(f"\n--- 基础信息 ---")
        print(f"  公司: {basic.get('公司名称', basic.get('Name', 'N/A'))}")
        print(f"  注册资本: {basic.get('注册资本', basic.get('RegistCapi', 'N/A'))}")
        print(f"  成立日期: {basic.get('成立日期', basic.get('StartDate', 'N/A'))}")
    
    # 风险信息
    risks = data.get('risks', {})
    lit_count = len(risks.get('litigation', []))
    pen_count = len(risks.get('penalties', []))
    dish_count = len(risks.get('dishonest', []))
    print(f"\n--- 风险信息 ---")
    print(f"  诉讼: {lit_count}条")
    print(f"  行政处罚: {pen_count}条")
    print(f"  失信: {dish_count}条")
    
    # 知识产权
    ip = data.get('ip', {})
    patent_count = len(ip.get('patents', []))
    trademark_count = len(ip.get('trademarks', []))
    copyright_count = len(ip.get('copyrights', []))
    print(f"\n--- 知识产权 ---")
    print(f"  专利: {patent_count}条")
    print(f"  商标: {trademark_count}条")
    print(f"  软著: {copyright_count}条")
    
    # 不一致项
    inconsistencies = data.get('inconsistencies', [])
    if inconsistencies:
        print(f"\n--- 不一致项 ({len(inconsistencies)}) ---")
        for item in inconsistencies[:5]:
            print(f"  - {item}")
    
    # 发现项摘要
    findings = data.get('findings_summary', '')
    if findings:
        print(f"\n--- 发现项摘要 ---")
        print(f"  {findings[:200]}")


def diff_caches(old_path, new_path):
    """比对两个缓存文件的差异"""
    old_data = load_cache(old_path)
    new_data = load_cache(new_path)
    
    changes = []
    
    # 比对诉讼
    old_lits = set(json.dumps(item, ensure_ascii=False) for item in old_data.get('risks', {}).get('litigation', []))
    new_lits = set(json.dumps(item, ensure_ascii=False) for item in new_data.get('risks', {}).get('litigation', []))
    added_lits = new_lits - old_lits
    removed_lits = old_lits - new_lits
    if added_lits:
        changes.append(f"新增诉讼 {len(added_lits)} 条")
    if removed_lits:
        changes.append(f"减少诉讼 {len(removed_lits)} 条")
    
    # 比对行政处罚
    old_pens = set(json.dumps(item, ensure_ascii=False) for item in old_data.get('risks', {}).get('penalties', []))
    new_pens = set(json.dumps(item, ensure_ascii=False) for item in new_data.get('risks', {}).get('penalties', []))
    added_pens = new_pens - old_pens
    if added_pens:
        changes.append(f"新增行政处罚 {len(added_pens)} 条")
    
    # 比对股权变更
    old_changes = set(json.dumps(item, ensure_ascii=False) for item in old_data.get('equity_changes', []))
    new_changes = set(json.dumps(item, ensure_ascii=False) for item in new_data.get('equity_changes', []))
    added_changes = new_changes - old_changes
    if added_changes:
        changes.append(f"新增股权变更 {len(added_changes)} 条")
    
    # 比对知识产权
    old_patents = set(json.dumps(item, ensure_ascii=False) for item in old_data.get('ip', {}).get('patents', []))
    new_patents = set(json.dumps(item, ensure_ascii=False) for item in new_data.get('ip', {}).get('patents', []))
    added_patents = new_patents - old_patents
    if added_patents:
        changes.append(f"新增专利 {len(added_patents)} 条")
    
    if changes:
        print(f"发现 {len(changes)} 类变更:")
        for change in changes:
            print(f"  - {change}")
    else:
        print("未发现显著变更")
    
    return changes


def export_cache(cache_path, output_path):
    """导出为可读 Markdown 报告"""
    data = load_cache(cache_path)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {data.get('project_name', 'N/A')} - 企查查数据报告\n\n")
        f.write(f"> 查询日期: {data.get('query_date', 'N/A')}\n\n")
        
        f.write("## 风险信息\n\n")
        risks = data.get('risks', {})
        f.write(f"- 诉讼: {len(risks.get('litigation', []))}条\n")
        f.write(f"- 行政处罚: {len(risks.get('penalties', []))}条\n")
        f.write(f"- 失信: {len(risks.get('dishonest', []))}条\n\n")
        
        f.write("## 知识产权\n\n")
        ip = data.get('ip', {})
        f.write(f"- 专利: {len(ip.get('patents', []))}条\n")
        f.write(f"- 商标: {len(ip.get('trademarks', []))}条\n")
        f.write(f"- 软著: {len(ip.get('copyrights', []))}条\n\n")
        
        findings = data.get('findings_summary', '')
        if findings:
            f.write("## 发现项摘要\n\n")
            f.write(f"{findings}\n\n")
        
        inconsistencies = data.get('inconsistencies', [])
        if inconsistencies:
            f.write("## 不一致项\n\n")
            for item in inconsistencies:
                f.write(f"- {item}\n")
    
    print(f"Report exported: {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='企查查缓存管理工具')
    subparsers = parser.add_subparsers(dest='command')
    
    # show
    show_parser = subparsers.add_parser('show', help='显示缓存摘要')
    show_parser.add_argument('cache_path', help='缓存文件路径')
    
    # diff
    diff_parser = subparsers.add_parser('diff', help='比对两个缓存差异')
    diff_parser.add_argument('old_cache', help='旧缓存文件路径')
    diff_parser.add_argument('new_cache', help='新缓存文件路径')
    
    # export
    export_parser = subparsers.add_parser('export', help='导出为可读报告')
    export_parser.add_argument('cache_path', help='缓存文件路径')
    export_parser.add_argument('output_path', help='输出报告路径')
    
    args = parser.parse_args()
    
    if args.command == 'show':
        show_cache(args.cache_path)
    elif args.command == 'diff':
        diff_caches(args.old_cache, args.new_cache)
    elif args.command == 'export':
        export_cache(args.cache_path, args.output_path)
    else:
        parser.print_help()
