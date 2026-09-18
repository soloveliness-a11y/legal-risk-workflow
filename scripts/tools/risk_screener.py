#!/usr/bin/env python3
import re
"""
风险初筛卡生成器 V1.0
从 qcc_cache.json 提取关键风险指标，按阈值生成红/黄/绿三色风险初筛卡。

用法:
  python3 risk_screener.py --qcc-cache ./01_dd_prep/qcc_cache.json --output ./01_dd_prep/risk_screening_card.md
  python3 risk_screener.py --qcc-cache ./qcc_cache.json --project-name "某公司"
  python3 risk_screener.py --qcc-cache ./qcc_cache.json --thresholds-file ./thresholds.json
  python3 risk_screener.py --init-thresholds
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


# ── 默认阈值配置 ──────────────────────────────────────────────

DEFAULT_THRESHOLDS = {
    "equity_pledge": {
        "description": "股权出质/冻结",
        "red": "实控人股权出质或冻结",
        "yellow": "非实控人股东股权出质或冻结",
        "green": "无股权出质或冻结记录"
    },
    "litigation": {
        "description": "诉讼风险",
        "red": "开庭公告≥5或存在重大诉讼",
        "yellow": "开庭公告2-4件",
        "green": "无诉讼或仅1件一般纠纷"
    },
    "administrative_penalty": {
        "description": "行政处罚",
        "red": "存在重大行政处罚",
        "yellow": "存在一般行政处罚（已整改）",
        "green": "无行政处罚"
    },
    "executed": {
        "description": "被执行人/失信",
        "red": "公司或实控人为失信被执行人",
        "yellow": "有被执行记录但已结案",
        "green": "无被执行人/失信记录"
    },
    "ipo_attempts": {
        "description": "IPO历史",
        "red": "IPO申报3次及以上未果",
        "yellow": "IPO申报1-2次未果",
        "green": "无IPO失败历史"
    },
    "registered_vs_paid_capital": {
        "description": "实缴比例",
        "red": "实缴比例<50%",
        "yellow": "实缴比例50%-80%",
        "green": "实缴比例>80%"
    },
    "shareholder_concentration": {
        "description": "股权集中度",
        "red": "实控人有效控制<25%",
        "yellow": "实控人有效控制25%-40%",
        "green": "实控人有效控制>40%"
    },
    "capital_reduction": {
        "description": "减资记录",
        "red": "报告期内减资且原因存疑",
        "yellow": "有减资记录但原因合理",
        "green": "无减资记录"
    }
}


# ── 阈值判定函数 ──────────────────────────────────────────────

def classify_equity_pledge(qcc_data):
    """股权出质/冻结"""
    risks = qcc_data.get("risks", {})
    eq = risks.get("equity_quality", "")
    controller = qcc_data.get("shareholders", {}).get("actual_controller", {})
    controller_name = controller.get("name", "")
    
    if not eq or eq == "无":
        return "green", "无股权出质或冻结记录"

    # 否定语义排除：字符串由否定词+目标词构成、且无年份/金额数字（真实出质冻结记录必含主体与编号）
    import re as _re
    if ("无" in eq or "未见" in eq or "未发现" in eq or "暂无" in eq) and ("出质" in eq or "冻结" in eq) \
            and not _re.search(r"\d{4}", eq) and not _re.search(r"\d+(\.\d+)?\s*万", eq):
        return "green", eq
    
    if controller_name and controller_name in eq:
        return "red", f"实控人{controller_name}股权存在出质或冻结"
    
    if "出质" in eq or "冻结" in eq:
        if "已解除" in eq:
            return "yellow", f"存在股权出质/冻结记录，但已解除：{eq}"
        return "yellow", f"非实控人股东股权出质或冻结：{eq}"
    
    return "green", eq


def classify_litigation(qcc_data):
    """诉讼风险"""
    risks = qcc_data.get("risks", {})
    lit = risks.get("litigation", {})
    
    if isinstance(lit, dict):
        count = lit.get("开庭公告", 0)
        overall = lit.get("整体风险", "")
        if count >= 5 or "高" in overall:
            return "red", f"开庭公告{count}件，整体风险{overall}"
        elif count >= 2:
            return "yellow", f"开庭公告{count}件，整体风险{overall}"
        else:
            return "green", f"开庭公告{count}件，整体风险{overall}"
    
    return "green", "未见诉讼风险"


def classify_administrative_penalty(qcc_data):
    """行政处罚"""
    risks = qcc_data.get("risks", {})
    penalty = risks.get("administrative_penalty", "")
    
    if not penalty or "未见" in penalty or "无" in penalty:
        return "green", "无行政处罚"
    
    if "重大" in penalty:
        return "red", penalty
    
    return "yellow", penalty


def classify_executed(qcc_data):
    """被执行人/失信"""
    risks = qcc_data.get("risks", {})
    executed = risks.get("executed_info", "")
    
    if not executed or "未见" in executed or "无" in executed:
        return "green", "无被执行人/失信记录"
    
    if "失信" in executed:
        return "red", executed
    
    return "yellow", executed


def classify_ipo_attempts(qcc_data):
    """IPO历史"""
    risks = qcc_data.get("risks", {})
    ipo = risks.get("ipo_history", [])
    
    if not ipo:
        return "green", "无IPO失败历史"
    
    failed = [i for i in ipo if i.get("status") in ("终止", "被否")]
    
    if len(failed) >= 3:
        details = "; ".join(f"{i.get('period', '')}({i.get('status', '')})" for i in failed)
        return "red", f"IPO申报{len(failed)}次未果：{details}"
    elif len(failed) >= 1:
        return "yellow", f"IPO申报{len(failed)}次未果"
    
    return "green", "有IPO历史但无明确失败记录"


def classify_capital(qcc_data):
    """实缴比例"""
    basic = qcc_data.get("basic_info", {})
    registered_str = basic.get("注册资本", "0")
    paid_str = basic.get("实缴资本", "0")

    def parse_amount(s):
        """解析金额字符串为数值（万元）。容错：仅取首个数字段，忽略括号备注与前后缀文字（如"12,345万（2025年增资后）"）。"""
        s = str(s)
        m = re.search(r"([\d,.]+)\s*(亿|万)?", s)
        if not m:
            return 0
        num = m.group(1).replace(",", "").replace("，", "").rstrip(".")
        if not num:
            return 0
        unit = m.group(2) or ""
        try:
            v = float(num)
        except ValueError:
            return 0
        if unit == "亿":
            return v * 10000
        return v

    registered = parse_amount(registered_str)
    paid = parse_amount(paid_str)
    if registered <= 0:
        return "yellow", f"注册资本信息无法解析：{registered_str}"
    ratio = paid / registered
    if ratio < 0.5:
        return "red", f"注册资本{registered_str}，实缴{paid_str}，比例{ratio:.1%}"
    elif ratio <= 0.8:
        return "yellow", f"注册资本{registered_str}，实缴{paid_str}，比例{ratio:.1%}"
    return "green", f"注册资本{registered_str}，实缴{paid_str}"



def classify_shareholder_concentration(qcc_data):
    """股权集中度"""
    controller = qcc_data.get("shareholders", {}).get("actual_controller", {})
    total_str = controller.get("total_effective_control", "")
    
    # 尝试提取百分比
    if not total_str:
        return "yellow", "无法确定实控人有效控制比例"
    
    # 提取数字（稳健化：无实控人表述或含多个百分比时不自动取首个——转人工判断）
    import re
    if "无实控" in total_str or "无实际控制" in total_str or len(re.findall(r'[\d.]+%', total_str)) > 1:
        return "yellow", f"控制权口径需人工判断：{total_str}"
    match = re.search(r'约?([\d.]+)%', total_str)
    if match:
        pct = float(match.group(1))
        if pct < 25:
            return "red", f"实控人有效控制{pct:.1f}%，控制力较弱"
        elif pct <= 40:
            return "yellow", f"实控人有效控制{pct:.1f}%"
        else:
            return "green", f"实控人有效控制{pct:.1f}%"
    
    return "yellow", f"实控人有效控制{total_str}"


def classify_capital_reduction(qcc_data):
    """减资记录"""
    risks = qcc_data.get("risks", {})
    reduction = risks.get("减资公告", "")
    
    if not reduction or "无" in reduction or "未见" in reduction:
        return "green", "无减资记录"
    
    if "有记录" in reduction:
        return "yellow", "存在减资公告记录，需进一步核查减资原因"
    
    return "yellow", reduction


# ── 分类器映射 ──────────────────────────────────────────────

CLASSIFIERS = {
    "equity_pledge": classify_equity_pledge,
    "litigation": classify_litigation,
    "administrative_penalty": classify_administrative_penalty,
    "executed": classify_executed,
    "ipo_attempts": classify_ipo_attempts,
    "registered_vs_paid_capital": classify_capital,
    "shareholder_concentration": classify_shareholder_concentration,
    "capital_reduction": classify_capital_reduction,
}

EMOJI_MAP = {"red": "🔴", "yellow": "🟡", "green": "🟢"}
LABEL_MAP = {"red": "高风险", "yellow": "关注", "green": "低风险"}


# ── 核心生成逻辑 ──────────────────────────────────────────────

def generate_screening_card(qcc_data, project_name=None):
    """生成风险初筛卡"""
    name = project_name or qcc_data.get("project_name", qcc_data.get("company_full_name", "未知项目"))
    
    results = []
    for key, classifier in CLASSIFIERS.items():
        level, detail = classifier(qcc_data)
        results.append({
            "key": key,
            "description": DEFAULT_THRESHOLDS[key]["description"],
            "level": level,
            "detail": detail
        })
    
    # 统计
    red_count = sum(1 for r in results if r["level"] == "red")
    yellow_count = sum(1 for r in results if r["level"] == "yellow")
    green_count = sum(1 for r in results if r["level"] == "green")
    
    # 总体评级
    if red_count >= 2:
        overall = "🔴 高风险"
        overall_detail = f"存在{red_count}项高风险指标，建议审慎评估"
    elif red_count >= 1:
        overall = "🟠 中高风险"
        overall_detail = f"存在{red_count}项高风险指标，需重点核查"
    elif yellow_count >= 4:
        overall = "🟡 中风险"
        overall_detail = f"存在{yellow_count}项关注指标，需进一步尽调"
    elif yellow_count >= 1:
        overall = "🟢 低风险（有关注项）"
        overall_detail = f"存在{yellow_count}项关注指标，整体风险可控"
    else:
        overall = "🟢 低风险"
        overall_detail = "各项指标均正常"
    
    # 生成 Markdown
    lines = []
    lines.append(f"# 风险初筛卡：{name}")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 数据来源：qcc_cache.json（工商数据缓存，数据源无关）")
    lines.append("")
    lines.append("## 总体评级")
    lines.append("")
    lines.append(f"**{overall}** — {overall_detail}")
    lines.append("")
    lines.append(f"统计：🔴 {red_count}项  🟡 {yellow_count}项  🟢 {green_count}项")
    lines.append("")
    
    # 按风险等级排序（红→黄→绿）
    order = {"red": 0, "yellow": 1, "green": 2}
    results.sort(key=lambda r: order[r["level"]])
    
    lines.append("## 指标明细")
    lines.append("")
    lines.append("| # | 指标 | 等级 | 说明 |")
    lines.append("|---|------|------|------|")
    for i, r in enumerate(results, 1):
        emoji = EMOJI_MAP[r["level"]]
        label = LABEL_MAP[r["level"]]
        lines.append(f"| {i} | {r['description']} | {emoji} {label} | {r['detail']} |")
    
    lines.append("")
    
    # 关键法律问题（如有）
    risks = qcc_data.get("risks", {})
    legal_issues = risks.get("关键法律问题_from_legal_dd", [])
    if legal_issues:
        lines.append("## 外部律所已识别风险（来自法律尽调报告）")
        lines.append("")
        for issue in legal_issues:
            lines.append(f"- {issue}")
        lines.append("")
    
    # 特殊标签
    tags = qcc_data.get("special_tags", [])
    if tags:
        lines.append("## 风险标签")
        lines.append("")
        lines.append(", ".join(f"`{t}`" for t in tags))
        lines.append("")
    
    # 免责声明
    lines.append("---")
    lines.append("*本初筛卡基于工商数据缓存（数据源无关 schema）自动生成，仅供参考，不构成投资建议。实际风险判断需结合完整尽调。*")
    
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="风险初筛卡生成器 — 从 qcc_cache.json 提取风险指标生成 Markdown 初筛卡"
    )
    parser.add_argument("--qcc-cache", type=str, help="qcc_cache.json 文件路径")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--project-name", type=str, help="项目名称（覆盖 qcc_cache.json 中的 project_name）")
    parser.add_argument("--init-thresholds", action="store_true", help="导出默认阈值配置到 thresholds.json")
    parser.add_argument("--thresholds-file", type=str, help="自定义阈值配置文件路径")
    
    args = parser.parse_args()
    
    # 导出默认阈值
    if args.init_thresholds:
        output_path = args.output or "risk_screener_thresholds.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_THRESHOLDS, f, ensure_ascii=False, indent=2)
        print(f"默认阈值配置已导出到: {output_path}")
        return
    
    # 必须提供 qcc_cache
    if not args.qcc_cache:
        parser.error("请提供 --qcc-cache 参数，或使用 --init-thresholds 导出默认阈值")
    
    cache_path = Path(args.qcc_cache)
    if not cache_path.exists():
        print(f"错误：文件不存在 {cache_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(cache_path, "r", encoding="utf-8") as f:
        qcc_data = json.load(f)
    
    card = generate_screening_card(qcc_data, args.project_name)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(card)
        print(f"风险初筛卡已生成: {output_path}")
    else:
        print(card)


if __name__ == "__main__":
    main()
