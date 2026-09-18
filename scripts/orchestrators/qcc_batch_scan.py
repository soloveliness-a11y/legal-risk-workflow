#!/usr/bin/env python3
"""
QCC 扫描编排器（legacy 示例）

状态：legacy/example——任务清单中的 qcc-company.get_* 为旧版 MCP 工具名，仅作采集
     维度参考，不代表当前数据源接口。当前数据源无关的采集规范见
     skills/qcc-scan/SKILL.md（工商数据源 CLI 适配器或手工采集模式）。

用途：为 dd-prep 步骤2生成结构化扫描任务清单，支持断点续扫和进度追踪。
设计理念：MCP 是 LLM 侧工具，Python 无法直接调用。
         本脚本负责"生成清单 + 记录进度 + 汇总结果"，
         LLM 按清单逐步执行 MCP 调用。

使用方式：
  # 1. 生成扫描任务清单
  python3 qcc_batch_scan.py plan --company "公司全称" --scope basic|extended|full --output-dir ./01_dd_prep

  # 2. 查看扫描进度
  python3 qcc_batch_scan.py status --scan-dir ./01_dd_prep

  # 3. 标记单个任务完成（LLM执行MCP后调用）
  python3 qcc_batch_scan.py mark --scan-dir ./01_dd_prep --task-id T01 --status done

  # 4. 批量更新进度（从 qcc_cache.json 自动匹配已完成项）
  python3 qcc_batch_scan.py sync --scan-dir ./01_dd_prep --cache ./01_dd_prep/qcc_cache.json

  # 5. 生成扫描摘要报告
  python3 qcc_batch_scan.py summary --scan-dir ./01_dd_prep

依赖：无外部依赖，纯标准库
数据格式：与 qcc_cache_manager.py 完全兼容
"""

import argparse
import json
import os
import sys
from datetime import datetime


# ── 扫描任务定义 ──────────────────────────────────────────────────────
# 完整18项MCP调用清单，按梯队分组
SCAN_TASKS = {
    "basic": [
        # 第一梯队（8项必调）
        {"id": "T01", "tool": "qcc-company.get_company_registration_info",
         "category": "工商基础", "desc": "公司注册基础信息", "tier": 1,
         "cache_key": "basic_info"},
        {"id": "T02", "tool": "qcc-company.get_shareholder_info",
         "category": "股权结构", "desc": "股东信息与持股比例", "tier": 1,
         "cache_key": "shareholders"},
        {"id": "T03", "tool": "qcc-company.get_change_records",
         "category": "历史变更", "desc": "工商变更记录", "tier": 1,
         "cache_key": "change_records"},
        {"id": "T04", "tool": "qcc-ipr.get_patent_info",
         "category": "知识产权", "desc": "专利信息", "tier": 1,
         "cache_key": "ip.patents"},
        {"id": "T05", "tool": "qcc-ipr.get_software_copyright_info",
         "category": "知识产权", "desc": "软件著作权", "tier": 1,
         "cache_key": "ip.software_copyrights"},
        {"id": "T06", "tool": "qcc-risk.get_lawsuit_info",
         "category": "风险信息", "desc": "诉讼信息", "tier": 1,
         "cache_key": "risks.litigation"},
        {"id": "T07", "tool": "qcc-risk.get_executed_info",
         "category": "风险信息", "desc": "被执行人信息", "tier": 1,
         "cache_key": "risks.executed_info"},
        {"id": "T08", "tool": "qcc-operation.get_financing_records",
         "category": "经营信息", "desc": "融资记录", "tier": 1,
         "cache_key": "financing"},
    ],
    "extended": [
        # 第二梯队（10项按需）
        {"id": "T09", "tool": "qcc-company.get_company_profile",
         "category": "工商基础", "desc": "公司概况详情", "tier": 2,
         "cache_key": "company_profile"},
        {"id": "T10", "tool": "qcc-company.get_key_personnel",
         "category": "工商基础", "desc": "主要人员（董监高）", "tier": 2,
         "cache_key": "key_personnel"},
        {"id": "T11", "tool": "qcc-company.get_external_investments",
         "category": "股权结构", "desc": "对外投资/子公司", "tier": 2,
         "cache_key": "external_investments"},
        {"id": "T12", "tool": "qcc-risk.get_administrative_penalty",
         "category": "风险信息", "desc": "行政处罚", "tier": 2,
         "cache_key": "risks.administrative_penalty"},
        {"id": "T13", "tool": "qcc-risk.get_equity_pledge_info",
         "category": "风险信息", "desc": "股权出质", "tier": 2,
         "cache_key": "risks.equity_pledge"},
        {"id": "T14", "tool": "qcc-ipr.get_trademark_info",
         "category": "知识产权", "desc": "商标信息", "tier": 2,
         "cache_key": "ip.trademarks"},
        {"id": "T15", "tool": "qcc-ipr.get_internet_service_info",
         "category": "知识产权", "desc": "ICP/APP/算法备案", "tier": 2,
         "cache_key": "ip.internet_services"},
        {"id": "T16", "tool": "qcc-operation.get_news_info",
         "category": "经营信息", "desc": "新闻舆情", "tier": 2,
         "cache_key": "news"},
        {"id": "T17", "tool": "qcc-risk.get_case_filing_info",
         "category": "风险信息", "desc": "立案信息", "tier": 2,
         "cache_key": "risks.case_filing"},
        {"id": "T18", "tool": "qcc-operation.get_bidding_info",
         "category": "经营信息", "desc": "招投标信息", "tier": 2,
         "cache_key": "bidding"},
    ],
}

# scope → 包含的任务组
SCOPE_MAP = {
    "basic": ["basic"],
    "extended": ["basic", "extended"],
    "full": ["basic", "extended"],
}


# ── 核心函数 ──────────────────────────────────────────────────────

def get_scan_file(scan_dir):
    """获取扫描进度文件路径"""
    return os.path.join(scan_dir, "qcc-scan_progress.json")


def load_progress(scan_dir):
    """加载扫描进度"""
    path = get_scan_file(scan_dir)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_progress(scan_dir, data):
    """保存扫描进度"""
    path = get_scan_file(scan_dir)
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def get_all_tasks(scope):
    """获取 scope 对应的全部任务列表"""
    tasks = []
    for group in SCOPE_MAP.get(scope, ["basic"]):
        tasks.extend(SCAN_TASKS.get(group, []))
    return tasks


def get_cache_value(cache_data, dot_key):
    """从缓存数据中按点分路径取值，如 'ip.patents'"""
    keys = dot_key.split('.')
    obj = cache_data
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k)
        else:
            return None
    return obj


# ── 命令：plan ──────────────────────────────────────────────────────

def cmd_plan(args):
    """生成扫描任务清单"""
    company = args.company
    scope = args.scope
    output_dir = args.output_dir

    tasks = get_all_tasks(scope)

    # 检查已有缓存，标记已完成项
    cache_path = os.path.join(output_dir, "qcc_cache.json")
    completed_keys = set()
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        for task in tasks:
            val = get_cache_value(cache_data, task["cache_key"])
            if val is not None and val != "" and val != [] and val != {}:
                completed_keys.add(task["id"])

    # 构建进度数据
    progress = {
        "meta": {
            "company": company,
            "scope": scope,
            "total_tasks": len(tasks),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "tasks": [],
    }

    for task in tasks:
        status = "done" if task["id"] in completed_keys else "pending"
        progress["tasks"].append({
            "id": task["id"],
            "tool": task["tool"],
            "category": task["category"],
            "desc": task["desc"],
            "tier": task["tier"],
            "cache_key": task["cache_key"],
            "status": status,
            "mcp_command": f'mcporter call {task["tool"]} searchKey="{company}"',
            "executed_at": None,
            "error": None,
        })

    path = save_progress(output_dir, progress)

    # 输出摘要
    done_count = len(completed_keys)
    pending_count = len(tasks) - done_count
    print(f"扫描任务清单已生成: {path}")
    print(f"公司: {company}")
    print(f"扫描范围: {scope} (共 {len(tasks)} 项)")
    print(f"已完成: {done_count} 项 (从缓存匹配)")
    print(f"待执行: {pending_count} 项")
    print()

    if pending_count > 0:
        print("待执行任务清单：")
        for t in progress["tasks"]:
            if t["status"] == "pending":
                tier_label = "必调" if t["tier"] == 1 else "按需"
                print(f"  [{t['id']}] [{tier_label}] {t['desc']}")
                print(f"        {t['mcp_command']}")
    else:
        print("所有任务已完成，无需额外扫描。")

    return progress


# ── 命令：status ──────────────────────────────────────────────────────

def cmd_status(args):
    """查看扫描进度"""
    progress = load_progress(args.scan_dir)
    if not progress:
        print("未找到扫描进度文件。请先运行 plan 命令。")
        return

    meta = progress["meta"]
    tasks = progress["tasks"]
    done = sum(1 for t in tasks if t["status"] == "done")
    failed = sum(1 for t in tasks if t["status"] == "failed")
    pending = sum(1 for t in tasks if t["status"] == "pending")

    print(f"公司: {meta['company']}")
    print(f"扫描范围: {meta['scope']}")
    print(f"创建时间: {meta['created_at']}")
    print(f"进度: {done}/{len(tasks)} 完成, {failed} 失败, {pending} 待执行")
    print()

    # 按状态分组显示
    if pending > 0:
        print(f"待执行 ({pending})：")
        for t in tasks:
            if t["status"] == "pending":
                tier_label = "必调" if t["tier"] == 1 else "按需"
                print(f"  [{t['id']}] [{tier_label}] {t['desc']}")

    if failed > 0:
        print(f"\n失败 ({failed})：")
        for t in tasks:
            if t["status"] == "failed":
                print(f"  [{t['id']}] {t['desc']} — {t.get('error', '未知错误')}")

    if done > 0:
        print(f"\n已完成 ({done})：")
        for t in tasks:
            if t["status"] == "done":
                tier_label = "必调" if t["tier"] == 1 else "按需"
                print(f"  [{t['id']}] [{tier_label}] {t['desc']}")


# ── 命令：mark ──────────────────────────────────────────────────────

def cmd_mark(args):
    """标记单个任务状态"""
    progress = load_progress(args.scan_dir)
    if not progress:
        print("未找到扫描进度文件。请先运行 plan 命令。")
        return

    task_id = args.task_id.upper()
    status = args.status

    if status not in ("done", "failed", "pending"):
        print(f"无效状态: {status}。可选: done, failed, pending")
        return

    found = False
    for t in progress["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            t["executed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if status == "failed" and args.error:
                t["error"] = args.error
            found = True
            break

    if not found:
        print(f"未找到任务: {task_id}")
        return

    progress["meta"]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_progress(args.scan_dir, progress)

    done = sum(1 for t in progress["tasks"] if t["status"] == "done")
    total = len(progress["tasks"])
    print(f"[{task_id}] 已标记为 {status}。总进度: {done}/{total}")


# ── 命令：sync ──────────────────────────────────────────────────────

def cmd_sync(args):
    """从 qcc_cache.json 自动同步已完成项"""
    progress = load_progress(args.scan_dir)
    if not progress:
        print("未找到扫描进度文件。请先运行 plan 命令。")
        return

    cache_path = args.cache
    if not os.path.exists(cache_path):
        print(f"缓存文件不存在: {cache_path}")
        return

    with open(cache_path, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)

    synced = 0
    for t in progress["tasks"]:
        if t["status"] == "done":
            continue
        val = get_cache_value(cache_data, t["cache_key"])
        if val is not None and val != "" and val != [] and val != {}:
            t["status"] = "done"
            t["executed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            synced += 1

    progress["meta"]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_progress(args.scan_dir, progress)

    done = sum(1 for t in progress["tasks"] if t["status"] == "done")
    total = len(progress["tasks"])
    print(f"从缓存同步了 {synced} 项。总进度: {done}/{total}")


# ── 命令：summary ──────────────────────────────────────────────────────

def cmd_summary(args):
    """生成扫描摘要报告"""
    progress = load_progress(args.scan_dir)
    if not progress:
        print("未找到扫描进度文件。请先运行 plan 命令。")
        return

    meta = progress["meta"]
    tasks = progress["tasks"]
    done = sum(1 for t in tasks if t["status"] == "done")
    failed = sum(1 for t in tasks if t["status"] == "failed")
    pending = sum(1 for t in tasks if t["status"] == "pending")

    report_lines = [
        f"# QCC 扫描摘要 — {meta['company']}",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 扫描范围: {meta['scope']} | 创建时间: {meta['created_at']}",
        "",
        "## 扫描进度",
        "",
        f"| 状态 | 数量 | 占比 |",
        f"|------|------|------|",
        f"| 已完成 | {done} | {done/len(tasks)*100:.0f}% |",
        f"| 失败 | {failed} | {failed/len(tasks)*100:.0f}% |",
        f"| 待执行 | {pending} | {pending/len(tasks)*100:.0f}% |",
        f"| **合计** | **{len(tasks)}** | **100%** |",
        "",
    ]

    if failed > 0:
        report_lines.append("## 失败任务")
        report_lines.append("")
        for t in tasks:
            if t["status"] == "failed":
                report_lines.append(f"- [{t['id']}] {t['desc']}: {t.get('error', '未知错误')}")
        report_lines.append("")

    if pending > 0:
        report_lines.append("## 待执行任务（复制到 LLM 执行）")
        report_lines.append("")
        report_lines.append("```")
        for t in tasks:
            if t["status"] == "pending":
                report_lines.append(t["mcp_command"])
        report_lines.append("```")
        report_lines.append("")

    # 已完成任务明细
    report_lines.append("## 已完成任务明细")
    report_lines.append("")
    report_lines.append("| ID | 梯队 | 分类 | 描述 | 完成时间 |")
    report_lines.append("|----|------|------|------|----------|")
    for t in tasks:
        if t["status"] == "done":
            tier_label = "必调" if t["tier"] == 1 else "按需"
            report_lines.append(f"| {t['id']} | {tier_label} | {t['category']} | {t['desc']} | {t.get('executed_at', '-')} |")
    report_lines.append("")

    report = "\n".join(report_lines)

    # 保存报告
    report_path = os.path.join(args.scan_dir, "qcc-scan_summary.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(report)
    print(f"\n摘要报告已保存: {report_path}")
    return report


# ── 主入口 ──────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='QCC 扫描编排器 — 生成任务清单、追踪进度、汇总结果',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用流程：
  1. plan    → 生成扫描任务清单（检查已有缓存，标记已完成项）
  2. LLM     → 按清单执行 MCP 调用，结果写入 qcc_cache.json
  3. sync    → 从缓存自动同步已完成项
  4. summary → 生成扫描摘要报告

示例：
  python3 qcc_batch_scan.py plan --company "某某科技有限公司" --scope basic --output-dir ./01_dd_prep
  python3 qcc_batch_scan.py status --scan-dir ./01_dd_prep
  python3 qcc_batch_scan.py mark --scan-dir ./01_dd_prep --task-id T01 --status done
  python3 qcc_batch_scan.py sync --scan-dir ./01_dd_prep --cache ./01_dd_prep/qcc_cache.json
  python3 qcc_batch_scan.py summary --scan-dir ./01_dd_prep
        """
    )
    subparsers = parser.add_subparsers(dest='command')

    # plan
    plan_p = subparsers.add_parser('plan', help='生成扫描任务清单')
    plan_p.add_argument('--company', required=True, help='公司完整全称（必须与企查查一致）')
    plan_p.add_argument('--scope', choices=['basic', 'extended', 'full'],
                        default='basic', help='扫描范围: basic(8项)|extended(18项)|full(18项)')
    plan_p.add_argument('--output-dir', required=True, help='输出目录（通常为项目的 01_dd_prep/）')

    # status
    status_p = subparsers.add_parser('status', help='查看扫描进度')
    status_p.add_argument('--scan-dir', required=True, help='扫描目录（包含 qcc-scan_progress.json）')

    # mark
    mark_p = subparsers.add_parser('mark', help='标记单个任务状态')
    mark_p.add_argument('--scan-dir', required=True, help='扫描目录')
    mark_p.add_argument('--task-id', required=True, help='任务ID（如 T01）')
    mark_p.add_argument('--status', required=True, choices=['done', 'failed', 'pending'], help='状态')
    mark_p.add_argument('--error', default=None, help='失败原因（status=failed时可选）')

    # sync
    sync_p = subparsers.add_parser('sync', help='从 qcc_cache.json 自动同步已完成项')
    sync_p.add_argument('--scan-dir', required=True, help='扫描目录')
    sync_p.add_argument('--cache', required=True, help='qcc_cache.json 路径')

    # summary
    summary_p = subparsers.add_parser('summary', help='生成扫描摘要报告')
    summary_p.add_argument('--scan-dir', required=True, help='扫描目录')

    args = parser.parse_args()

    if args.command == 'plan':
        cmd_plan(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'mark':
        cmd_mark(args)
    elif args.command == 'sync':
        cmd_sync(args)
    elif args.command == 'summary':
        cmd_summary(args)
    else:
        parser.print_help()
