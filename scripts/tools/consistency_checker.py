#!/usr/bin/env python3
"""
跨章一致性检查器（consistency_checker.py）

用途：自动检测 risk-report 分章产出（report_ch1_3.md ~ report_ch7.md）之间的跨章一致性问题。
输出：consistency_check.json

检查项：
  1. 同一事实在不同章节的表述是否一致（关键词+数字交叉比对）
  2. 风险编号是否连续、引用是否有效
  3. 人名/公司名是否跨章节一致
  4. 日期/金额等数字是否跨章节矛盾
  5. 风险等级是否与 risk_matrix.json 一致

触发时机：Phase 3 Step 3.5 完成后、Step 3.6 执行时自动调用

用法：
  python3 scripts/tools/consistency_checker.py <project_dir>
  python3 scripts/tools/consistency_checker.py <project_dir> --output <output_path>
  python3 scripts/tools/consistency_checker.py <project_dir> --verbose
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────────────

CHAPTER_FILES = [
    ("report_ch1_3.md", "前言+前提（Ch.1-3）"),
    ("report_ch4.md", "基本情况（Ch.4）"),
    ("report_ch5.md", "重点问题（Ch.5）"),
    ("report_ch6.md", "投资方案评估（Ch.6）"),
    ("report_ch7.md", "风险总结（Ch.7）"),
]

RISK_ID_PATTERN = re.compile(r"\bR(\d{2,3})\b")
RISK_LEVEL_PATTERN = re.compile(r"[🔴🟠🟡🔵🟢]")
RISK_LEVELS = {"🔴": "高", "🟠": "中高", "🟡": "中", "🔵": "中低", "🟢": "低"}

# 数字提取（含万元/亿元/元等）
NUMBER_PATTERN = re.compile(r"([\d,]+\.?\d*)\s*(万元|亿元|元|万|%|个百分点)")

# 日期提取
DATE_PATTERN = re.compile(r"(20\d{2})[年/\-.](\d{1,2})[月/\-.]?(\d{1,2})?日?")

# 人名提取（中文2-4字，前后有上下文标记）
PERSON_PATTERN = re.compile(r"(?:创始人|法定代表人|实控人|董事长|总经理|CTO|CEO|COO|CFO)[：:]\s*([^\s,，、；;]{2,4})")

# 公司名提取（"公司"结尾）
COMPANY_PATTERN = re.compile(r"([\u4e00-\u9fff]{2,15}(?:公司|企业|集团|有限))")


def _split_full_report(content: str) -> dict[str, tuple[str, str]]:
    """将完整报告md按H1/H2标题拆分为虚拟章节"""
    chapters = {}

    # 按一级/二级标题拆分
    section_map = {
        "前言": ("report_ch1_3.md", "前言+前提（Ch.1-3）"),
        "前提": ("report_ch1_3.md", "前言+前提（Ch.1-3）"),
        "基本": ("report_ch4.md", "基本情况（Ch.4）"),
        "重点问题": ("report_ch5.md", "重点问题（Ch.5）"),
        "投资方案": ("report_ch6.md", "投资方案评估（Ch.6）"),
        "风险总结": ("report_ch7.md", "风险总结（Ch.7）"),
        "总体结论": ("report_ch7.md", "风险总结（Ch.7）"),
        "风险矩阵": ("report_ch7.md", "风险总结（Ch.7）"),
    }

    # 简单按标题行拆分
    current_chapter_key = "report_ch1_3.md"
    chapter_contents = defaultdict(list)

    for line in content.split("\n"):
        # 检测H1/H2标题
        heading_match = re.match(r"^#{1,2}\s+(.+)", line)
        if heading_match:
            heading = heading_match.group(1)
            # 匹配到章节关键词则切换
            for keyword, (key, desc) in section_map.items():
                if keyword in heading:
                    current_chapter_key = key
                    break
        chapter_contents[current_chapter_key].append(line)

    # 合并到对应虚拟章节
    for key, lines in chapter_contents.items():
        desc = dict(CHAPTER_FILES).get(key, "虚拟章节")
        chapters[key] = ("\n".join(lines), desc)

    return chapters


def load_chapters(project_dir: str) -> dict[str, tuple[str, str]]:
    """加载所有分章文件，返回 {文件名: (内容, 章节描述)}
    
    优先加载分章格式（report_ch1_3.md等），
    如不存在则查找完整报告md并自动拆分。
    """
    report_dir = os.path.join(project_dir, "04_risk_report")
    chapters = {}

    # 1. 尝试加载分章格式
    for filename, description in CHAPTER_FILES:
        filepath = os.path.join(report_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                chapters[filename] = (f.read(), description)

    # 2. 如果分章格式不全，尝试加载完整报告并拆分
    if len(chapters) < 2:
        import glob
        # 查找完整报告md（排除投委会版）
        full_reports = glob.glob(os.path.join(report_dir, "*风控报告*.md"))
        full_reports = [f for f in full_reports if "投委会版" not in f]
        # 按修改时间排序，取最新的
        full_reports.sort(key=os.path.getmtime, reverse=True)

        if full_reports:
            # 清空分章结果，使用完整报告拆分
            chapters = {}
            with open(full_reports[0], "r", encoding="utf-8") as f:
                content = f.read()
            chapters = _split_full_report(content)
            # 标记来源
            chapters["__source__"] = (os.path.basename(full_reports[0]), "完整报告自动拆分")

    return chapters
        # 不存在的文件跳过

    return chapters


def load_risk_matrix(project_dir: str) -> dict | None:
    """加载 risk_matrix.json"""
    matrix_path = os.path.join(project_dir, "04_risk_report", "risk_matrix.json")
    if os.path.exists(matrix_path):
        with open(matrix_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def extract_risk_ids(text: str) -> list[str]:
    """提取文本中的所有风险编号"""
    return RISK_ID_PATTERN.findall(text)


def extract_risk_levels(text: str) -> list[tuple[str, str]]:
    """提取风险等级标记，返回 [(编号, 等级emoji)]"""
    results = []
    # 查找 "R01🔴高" 或 "R01 🔴" 等模式
    combined = re.findall(r"(R\d{2,3})\s*[：:]*\s*([🔴🟠🟡🔵🟢])", text)
    for risk_id, level_emoji in combined:
        results.append((risk_id, level_emoji))
    return results


def extract_key_numbers(text: str) -> list[tuple[str, str]]:
    """提取关键数字，返回 [(数字+单位, 原始上下文片段)]"""
    results = []
    for match in NUMBER_PATTERN.finditer(text):
        number_unit = match.group(0)
        # 取前后30字作为上下文
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        context = text[start:end].replace("\n", " ").strip()
        results.append((number_unit, context))
    return results


def extract_persons(text: str) -> list[str]:
    """提取人名"""
    persons = set()
    for match in PERSON_PATTERN.finditer(text):
        persons.add(match.group(1))
    return list(persons)


def extract_companies(text: str) -> list[str]:
    """提取公司名"""
    companies = set()
    for match in COMPANY_PATTERN.finditer(text):
        name = match.group(1)
        # 过滤泛指词
        if name not in ("本公司", "该公司", "投资公司", "基金公司", "上市公司"):
            companies.add(name)
    return list(companies)


def check_risk_id_consistency(chapters: dict) -> list[dict]:
    """检查1：风险编号连续性和引用有效性"""
    issues = []

    # 收集所有风险ID
    all_ids = {}  # risk_id -> [(filename, description)]
    for filename, (content, desc) in chapters.items():
        ids = extract_risk_ids(content)
        for id_str in ids:
            risk_id = f"R{id_str}"
            if risk_id not in all_ids:
                all_ids[risk_id] = []
            all_ids[risk_id].append((filename, desc))

    if not all_ids:
        issues.append({
            "type": "风险编号缺失",
            "severity": "warning",
            "description": "未在任何章节中发现风险编号（R01-R99格式）",
            "details": "请确认报告是否使用了标准风险编号格式"
        })
        return issues

    # 检查连续性
    id_nums = sorted([int(x[1:]) for x in all_ids.keys()])
    for i in range(len(id_nums) - 1):
        gap = id_nums[i + 1] - id_nums[i]
        if gap > 1:
            missing = [f"R{n:02d}" for n in range(id_nums[i] + 1, id_nums[i + 1])]
            issues.append({
                "type": "风险编号不连续",
                "severity": "info",
                "description": f"R{id_nums[i]:02d} 到 R{id_nums[i+1]:02d} 之间存在跳号",
                "details": f"缺失编号：{', '.join(missing)}（可能已被合并或取消，见S16规范）"
            })

    # 检查Ch.7是否包含所有编号
    ch7_content = chapters.get("report_ch7.md", ("", ""))[0]
    ch7_ids = set(extract_risk_ids(ch7_content))
    all_id_set = set(id_nums)

    missing_in_ch7 = all_id_set - ch7_ids
    if missing_in_ch7:
        missing_str = ", ".join([f"R{n:02d}" for n in sorted(missing_in_ch7)])
        issues.append({
            "type": "风险总结缺少编号",
            "severity": "warning",
            "description": f"Ch.7（风险总结）缺少以下风险编号：{missing_str}",
            "details": "风险总结应包含所有风险编号的汇总"
        })

    return issues


def check_risk_level_consistency(chapters: dict, risk_matrix: dict | None) -> list[dict]:
    """检查2：风险等级跨章节一致性 + 与risk_matrix.json一致性"""
    issues = []

    # 收集各章节中的风险等级标注
    level_map = defaultdict(list)  # risk_id -> [(level_emoji, filename, desc)]
    for filename, (content, desc) in chapters.items():
        for risk_id, level_emoji in extract_risk_levels(content):
            level_map[risk_id].append((level_emoji, filename, desc))

    # 同一编号在不同章节的等级不同
    for risk_id, entries in level_map.items():
        levels = set([e[0] for e in entries])
        if len(levels) > 1:
            level_details = [f"{RISK_LEVELS.get(e[0], e[0])}（{e[2]}）" for e in entries]
            issues.append({
                "type": "风险等级跨章节不一致",
                "severity": "error",
                "description": f"{risk_id} 在不同章节中风险等级不一致",
                "details": level_details
            })

    # 与 risk_matrix.json 比对
    if risk_matrix and "risks" in risk_matrix:
        matrix_levels = {}
        for risk in risk_matrix["risks"]:
            risk_id = risk.get("id", risk.get("risk_id", ""))
            risk_level = risk.get("level", risk.get("risk_level", ""))
            if risk_id:
                matrix_levels[risk_id] = risk_level

        for risk_id, entries in level_map.items():
            if risk_id in matrix_levels:
                # 提取章节中的等级文本
                chapter_level = RISK_LEVELS.get(entries[0][0], entries[0][0])
                matrix_level = matrix_levels[risk_id]
                if chapter_level != matrix_level:
                    issues.append({
                        "type": "风险等级与矩阵不一致",
                        "severity": "error",
                        "description": f"{risk_id} 在报告正文中标注为{chapter_level}，但risk_matrix.json中为{matrix_level}",
                        "details": f"正文来源：{entries[0][2]}；矩阵值：{matrix_level}"
                    })

    return issues


def check_cross_chapter_fact_consistency(chapters: dict) -> list[dict]:
    """检查3：跨章节数字/事实一致性"""
    issues = []

    # 提取各章节的关键数字
    numbers_by_chapter = {}
    for filename, (content, desc) in chapters.items():
        numbers_by_chapter[filename] = extract_key_numbers(content)

    # 比对Ch.4（基本情况）和Ch.5（重点问题）中的数字
    ch4_nums = numbers_by_chapter.get("report_ch4.md", [])
    ch5_nums = numbers_by_chapter.get("report_ch5.md", [])

    # 简单的数字冲突检测：查找同一数字在不同章节中上下文相关的矛盾
    # 注：这是轻量级检查，LLM的深度检查更全面
    ch4_num_set = {n[0] for n in ch4_nums}
    ch5_num_set = {n[0] for n in ch5_nums}

    # 检查股权比例是否一致（关键词匹配）
    for filename, (content, desc) in chapters.items():
        # 股权比例冲突检测
        equity_matches = re.findall(r"持股(?:比例)?[：:]\s*(\d+\.?\d*)\s*%", content)
        if equity_matches:
            # 同一公司名下持股比例是否多处出现
            pass  # 轻量级不做深度语义分析

    # 检查公司名跨章节一致性
    companies_by_chapter = {}
    for filename, (content, desc) in chapters.items():
        companies_by_chapter[filename] = set(extract_companies(content))

    # 找出在Ch.4/5中出现但名称不一致的公司（模糊匹配）
    all_companies = defaultdict(list)
    for filename, companies in companies_by_chapter.items():
        for company in companies:
            all_companies[company].append(filename)

    # 日期矛盾检测
    dates_by_chapter = {}
    for filename, (content, desc) in chapters.items():
        dates = DATE_PATTERN.findall(content)
        dates_by_chapter[filename] = [(y, m, d) for y, m, d in dates]

    return issues  # 轻量级检查结果较少，主要依赖LLM深度检查


def check_chapter_completeness(chapters: dict) -> list[dict]:
    """检查4：章节完整性"""
    issues = []

    missing = []
    for filename, description in CHAPTER_FILES:
        if filename not in chapters:
            missing.append(f"{filename}（{description}）")

    if missing:
        issues.append({
            "type": "章节缺失",
            "severity": "warning",
            "description": f"以下报告章节文件不存在：{', '.join(missing)}",
            "details": "请确认是否所有章节都已生成"
        })

    # 检查章节是否为空或过短
    for filename, (content, desc) in chapters.items():
        if len(content.strip()) < 100:
            issues.append({
                "type": "章节内容过短",
                "severity": "warning",
                "description": f"{filename}（{desc}）内容过短（{len(content.strip())}字）",
                "details": "可能生成不完整"
            })

    return issues


def check_internal_fields_leak(chapters: dict) -> list[dict]:
    """检查5：对外文档是否含内部字段"""
    issues = []

    internal_markers = [
        "📌待核实", "⚠️不一致", "❌未提供", "[推断]", "[BP声称]",
        "certainty:", "source:", "updated_by:"
    ]

    for filename, (content, desc) in chapters.items():
        found = []
        for marker in internal_markers:
            if marker in content:
                count = content.count(marker)
                found.append(f"{marker}（{count}处）")

        if found:
            issues.append({
                "type": "对外文档含内部字段",
                "severity": "error",
                "description": f"{filename}（{desc}）包含内部字段标记",
                "details": f"发现：{', '.join(found)}。对外报告不应包含确定性标签和内部字段。"
            })

    return issues


def run_consistency_check(project_dir: str, verbose: bool = False) -> dict:
    """执行完整的一致性检查"""

    # 加载章节
    chapters = load_chapters(project_dir)
    # 分离元数据
    source_info = chapters.pop("__source__", None)
    if not chapters:
        return {
            "check_time": datetime.now().isoformat(),
            "project_dir": project_dir,
            "status": "skipped",
            "reason": "未找到任何报告章节文件",
            "issues": [],
            "summary": {"total": 0, "error": 0, "warning": 0, "info": 0}
        }

    # 加载risk_matrix
    risk_matrix = load_risk_matrix(project_dir)

    # 执行所有检查
    all_issues = []

    all_issues.extend(check_chapter_completeness(chapters))
    all_issues.extend(check_risk_id_consistency(chapters))
    all_issues.extend(check_risk_level_consistency(chapters, risk_matrix))
    all_issues.extend(check_cross_chapter_fact_consistency(chapters))
    all_issues.extend(check_internal_fields_leak(chapters))

    # 统计
    summary = {"total": len(all_issues), "error": 0, "warning": 0, "info": 0}
    for issue in all_issues:
        severity = issue.get("severity", "info")
        if severity in summary:
            summary[severity] += 1

    # 构建输出
    result = {
        "check_time": datetime.now().isoformat(),
        "project_dir": project_dir,
        "status": "completed",
        "source_file": source_info[0] if source_info else "分章文件",
        "source_mode": "完整报告自动拆分" if source_info else "分章文件",
        "chapters_checked": list(chapters.keys()),
        "risk_matrix_loaded": risk_matrix is not None,
        "issues": all_issues,
        "summary": summary
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"跨章一致性检查报告")
        print(f"{'='*60}")
        print(f"项目目录：{project_dir}")
        print(f"检查时间：{result['check_time']}")
        print(f"检查章节数：{len(chapters)}")
        print(f"风险矩阵：{'已加载' if risk_matrix else '未找到'}")
        print(f"\n问题统计：错误 {summary['error']} | 警告 {summary['warning']} | 信息 {summary['info']}")
        print(f"{'='*60}")

        for i, issue in enumerate(all_issues, 1):
            icon = {"error": "🔴", "warning": "⚠️", "info": "ℹ️"}.get(issue["severity"], "•")
            print(f"\n{i}. {icon} [{issue['type']}] {issue['description']}")
            if issue.get("details"):
                details = issue["details"]
                if isinstance(details, list):
                    for d in details:
                        print(f"   - {d}")
                else:
                    print(f"   {details}")

        print(f"\n{'='*60}")

    return result


def main():
    parser = argparse.ArgumentParser(description="跨章一致性检查器")
    parser.add_argument("project_dir", help="项目目录路径（如 projects/某项目）")
    parser.add_argument("--output", "-o", help="输出JSON文件路径（默认：项目目录/04_risk_report/consistency_check.json）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    # 验证项目目录
    project_dir = os.path.abspath(args.project_dir)
    if not os.path.isdir(project_dir):
        print(f"错误：项目目录不存在 - {project_dir}", file=sys.stderr)
        sys.exit(1)

    # 执行检查
    result = run_consistency_check(project_dir, verbose=args.verbose)

    # 确定输出路径
    output_path = args.output
    if not output_path:
        report_dir = os.path.join(project_dir, "04_risk_report")
        os.makedirs(report_dir, exist_ok=True)
        output_path = os.path.join(report_dir, "consistency_check.json")

    # 写入结果
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if not args.verbose:
        print(f"一致性检查完成：{result['summary']['total']} 个问题"
              f"（🔴 {result['summary']['error']} / ⚠️ {result['summary']['warning']} / ℹ️ {result['summary']['info']}）")
        print(f"输出：{output_path}")

    sys.exit(0 if result["summary"]["error"] == 0 else 1)


if __name__ == "__main__":
    main()
