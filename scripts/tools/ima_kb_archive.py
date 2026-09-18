#!/usr/bin/env python3
"""
IMA 知识库归档工具 V2.0（兼容入口）

⚠️  本文件现为兼容层，核心 API 调用已迁移至 capabilities/ima_archive.py。

数据边界：--import-urls / --from-research / --from-sources 会把 URL 列表发送到
外部 IMA 服务，属项目信息外传，须加 --allow-external-send 或在 config.yaml 设
ima.allow_send: true；--list / --list-content / --list-folders 为只读操作不受限。
详见 SECURITY_PRIVACY.md。

用法：
  python3 ima_kb_archive.py --list
  python3 ima_kb_archive.py --list-content "某项目知识库"
  python3 ima_kb_archive.py --allow-external-send --import-urls "https://..." --kb "某项目知识库" --folder "行业研究"
  python3 ima_kb_archive.py --allow-external-send --from-research research_01.md --kb "某项目知识库"
"""

import sys
import os
import argparse
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_SCRIPTS_DIR = os.path.join(_SCRIPT_DIR, "..")
for _p in (_SCRIPT_DIR, _REPO_SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from capabilities.ima_archive import (
    list_kbs, list_kb_content, find_kb_id, find_folder_id,
    import_urls, auto_match_folder,
    extract_urls_from_file, extract_urls_from_sources,
)
from config_loader import get_config


def _print_items(items, indent=2):
    type_map = {1: "📄", 2: "🌐", 3: "📄", 4: "📊", 5: "📈", 7: "📝",
                9: "🖼️", 11: "📝", 13: "📄", 14: "🖼️", 15: "🎵", 99: "📁"}
    prefix = " " * indent
    for i, item in enumerate(items, 1):
        title = item.get("title", "无标题")
        media_type = item.get("media_type", "?")
        icon = type_map.get(media_type, "📎")
        print(f"{prefix}{i}. {icon} {title}")


def _list_folders(kb_name):
    kb_id = find_kb_id(kb_name)
    if not kb_id:
        print(f"❌ 未找到知识库: {kb_name}")
        return
    folders = []
    for query in ["资料", "研究", "文件", "协议"]:
        result = __import__('capabilities.ima_archive', fromlist=['ima_api']).ima_api(
            "openapi/wiki/v1/search_knowledge", {"query": query, "knowledge_base_id": kb_id, "cursor": ""}
        )
        if result.get("code") == 0:
            for item in result.get("data", {}).get("info_list", []):
                if item.get("media_type") == 99:
                    fid = item.get("media_id", "")
                    if not any(f.get("media_id") == fid for f in folders):
                        folders.append(item)
    if not folders:
        print(f"📂 {kb_name} 中没有文件夹")
        return
    print(f"📂 {kb_name} 的文件夹（共 {len(folders)} 个）\n")
    for f in folders:
        print(f"  📁 {f.get('title', '未命名')}")


def main():
    parser = argparse.ArgumentParser(
        description="IMA 知识库归档工具 V2.0",
        epilog="导入类操作会将 URL 列表发送到外部 IMA 服务，须加 --allow-external-send。",
    )
    parser.add_argument("--list", action="store_true", help="列出所有知识库")
    parser.add_argument("--list-content", metavar="KB_NAME", help="列出知识库内容")
    parser.add_argument("--list-folders", metavar="KB_NAME", help="列出知识库中的所有文件夹")
    parser.add_argument("--import-urls", nargs="+", metavar="URL", help="导入URL到知识库（外传操作）")
    parser.add_argument("--from-research", metavar="FILE", help="从 research_*.md 提取URL并导入（外传操作）")
    parser.add_argument("--from-sources", metavar="FILE", help="从 sources_*.json 提取URL并导入（外传操作）")
    parser.add_argument("--kb", required=False, default="行业研究", help="目标知识库名称")
    parser.add_argument("--folder", help="目标文件夹名称")
    parser.add_argument("--auto-folder", action="store_true", help="自动匹配文件夹")
    parser.add_argument("--allow-external-send", action="store_true",
                        help="确认将 URL 列表发送到外部 IMA 服务")

    args = parser.parse_args()

    send_ops = args.import_urls or args.from_research or args.from_sources
    if send_ops and not (args.allow_external_send or get_config().get_bool("ima.allow_send", False)):
        print(
            "⛔ 未获外传确认：导入操作会把 URL 列表发送到外部 IMA 服务。\n"
            "   确认后加 --allow-external-send 重试，或在 config.yaml 设置 ima.allow_send: true。\n"
            "   数据边界说明见 SECURITY_PRIVACY.md。",
            file=sys.stderr,
        )
        sys.exit(4)

    if args.list:
        kbs = list_kbs()
        print(f"📚 IMA 知识库列表（共 {len(kbs)} 个）\n")
        for kb in kbs:
            print(f"  • {kb['kb_name']}")
        return

    if args.list_content:
        items = list_kb_content(args.list_content)
        _print_items(items)
        return

    if args.list_folders:
        _list_folders(args.list_folders)
        return

    if args.import_urls:
        result = import_urls(args.import_urls, args.kb, args.folder)
        print(f"\n📊 导入完成: ✅ {result['success']} 成功 / ❌ {result['fail']} 失败")
        return

    if args.from_research:
        fp = args.from_research
        if not Path(fp).exists():
            print(f"❌ 文件不存在: {fp}")
            sys.exit(1)
        urls = extract_urls_from_file(fp)
        print(f"📋 提取到 {len(urls)} 个 URL")
        folder = None
        if args.auto_folder:
            kb_id = find_kb_id(args.kb)
            if kb_id:
                folder = auto_match_folder(fp, kb_id)
        result = import_urls(urls, args.kb, folder or args.folder)
        print(f"\n📊 导入完成: ✅ {result['success']} 成功 / ❌ {result['fail']} 失败")
        return

    if args.from_sources:
        fp = args.from_sources
        if not Path(fp).exists():
            print(f"❌ 文件不存在: {fp}")
            sys.exit(1)
        urls = extract_urls_from_sources(fp)
        print(f"📋 提取到 {len(urls)} 个 URL")
        result = import_urls(urls, args.kb, args.folder)
        print(f"\n📊 导入完成: ✅ {result['success']} 成功 / ❌ {result['fail']} 失败")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
