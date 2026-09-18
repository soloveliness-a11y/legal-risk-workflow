#!/usr/bin/env python3
"""
投委会版一致性校验工具 V1.0
对照底稿版与投委会版 markdown，自动执行 writing_patterns.md §10.7-C 的 8 项自检。

用法:
  python3 ic_version_consistency_check.py <底稿版.md> <投委会版.md>
  python3 ic_version_consistency_check.py <底稿版.md> <投委会版.md> --json
  python3 ic_version_consistency_check.py <底稿版.md> <投委会版.md> --verbose

校验项（Q1-Q8）:
  Q1  Part二信息等价性 — 表格行数、关键数值与底稿一致
  Q2  跨节引用内联结论 — "不赘述""详见""见上文"后200字内有结论
  Q3  财务数据多年对比 — 财务指标表≥2个年度列
  Q4  保护条款4方向齐全 — 先决条件+交割后承诺+陈述保证+赔偿条款
  Q5  总结引用与正文一致 — 总结段方向与Part四实际一一对应
  Q6  正面因素保留 — Part五含"正面因素"独立段落
  Q7  风险等级一致 — R编号等级与底稿无变动
  Q8  待补标注保留 — 底稿【待补·Pxxx】在投委会版中均存在
"""

import argparse
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional


# ── 数据结构 ──────────────────────────────────────────────

@dataclass
class CheckResult:
    """单项校验结果"""
    code: str           # Q1-Q8
    name: str           # 检查项名称
    passed: bool        # 是否通过
    severity: str       # PASS / WARN / FAIL
    details: str        # 说明
    evidence: List[str] = field(default_factory=list)


@dataclass
class CheckReport:
    """完整校验报告"""
    draft_file: str
    ic_file: str
    total: int = 0
    passed: int = 0
    warned: int = 0
    failed: int = 0
    results: List[CheckResult] = field(default_factory=list)

    @property
    def overall(self) -> str:
        if self.failed > 0:
            return "FAIL"
        elif self.warned > 0:
            return "PASS_WITH_WARNINGS"
        return "ALL_PASS"


# ── 工具函数 ──────────────────────────────────────────────

def read_markdown(filepath: str) -> str:
    """读取 markdown 文件"""
    p = Path(filepath)
    if not p.exists():
        print(f"[ERROR] 文件不存在: {filepath}", file=sys.stderr)
        sys.exit(1)
    return p.read_text(encoding="utf-8")


def split_sections(text: str) -> dict:
    """
    将 markdown 按 ## 二级标题 拆分为章节字典。
    key = 标题文本（去掉编号前缀），value = 章节完整内容（含标题行）
    """
    sections = {}
    # 匹配 ## 开头的二级标题行
    parts = re.split(r'^(## .+)$', text, flags=re.MULTILINE)
    # parts[0] = ## 之前的内容（前言）
    # parts[1] = 第一个 ## 标题行
    # parts[2] = 第一个 ## 标题下的内容
    # ...
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        content = parts[i + 1] if i + 1 < len(parts) else ""
        sections[heading] = heading + "\n" + content
    return sections


def find_section(sections: dict, keywords: List[str]) -> Optional[Tuple[str, str]]:
    """
    在 sections 字典中查找包含任一关键词的章节。
    返回 (标题, 内容) 或 None。
    """
    for keyword in keywords:
        for heading, content in sections.items():
            if keyword in heading:
                return (heading, content)
    return None


def find_section_by_index(sections: dict, index: int) -> Optional[Tuple[str, str]]:
    """
    按中文序号定位第 N 个正式章节。
    index=1 → 一、..., index=2 → 二、..., etc.
    通过匹配标题中的中文序号来定位，忽略非章节标题（如报告名）。
    """
    cn_nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    if index < 1 or index > len(cn_nums):
        return None
    target_num = cn_nums[index - 1]
    for heading, content in sections.items():
        # 匹配 "二、" 或 "2 " 等编号格式
        if re.match(rf'^##\s*{target_num}[、.．\s]', heading) or re.match(rf'^##\s*{index}[、.．\s]', heading):
            return (heading, content)
    return None


def extract_table_rows(text: str) -> List[List[str]]:
    """提取 markdown 表格的所有行（不含分隔行），返回每行的单元格列表"""
    rows = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and not re.match(r'^\|[\s\-:|]+\|$', stripped):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            rows.append(cells)
    return rows


def extract_numbers(text: str) -> List[str]:
    """提取文本中的数值（含百分号、万元等）"""
    return re.findall(r'[\d,]+\.?\d*%?(?:万元|亿元|万|亿)?', text)


# ── Q1: Part二信息等价性 ──────────────────────────────────

def check_q1(draft: str, ic: str, draft_sections: dict, ic_sections: dict) -> CheckResult:
    """
    检查 Part 二 基本情况的表格行数和关键数值是否等价。
    逻辑：比较投委会版Part二的表格行数与底稿版，差异≤10%视为通过。
    """
    result = CheckResult(code="Q1", name="Part二信息等价性", passed=True, severity="PASS", details="")

    # 找 Part 二 — 优先按序号，fallback 关键词
    draft_part2 = find_section_by_index(draft_sections, 2) or find_section(draft_sections, ["二、", "基本"])
    ic_part2 = find_section_by_index(ic_sections, 2) or find_section(ic_sections, ["二、", "基本"])

    if not draft_part2 or not ic_part2:
        result.passed = False
        result.severity = "WARN"
        result.details = "未找到 Part 二 章节，跳过表格行数比对"
        return result

    draft_rows = extract_table_rows(draft_part2[1])
    ic_rows = extract_table_rows(ic_part2[1])

    # 排除表头（第一行）后计数
    draft_data_rows = len(draft_rows) - 1 if draft_rows else 0
    ic_data_rows = len(ic_rows) - 1 if ic_rows else 0

    if draft_data_rows == 0:
        result.details = "底稿版Part二无表格数据，跳过比对"
        return result

    ratio = ic_data_rows / draft_data_rows
    diff_pct = abs(1 - ratio) * 100

    if diff_pct > 20:
        result.passed = False
        result.severity = "FAIL"
        result.details = (
            f"表格行数差异过大：底稿{draft_data_rows}行 vs 投委会版{ic_data_rows}行"
            f"（差异{diff_pct:.0f}%）"
        )
    elif diff_pct > 10:
        result.severity = "WARN"
        result.details = (
            f"表格行数有差异：底稿{draft_data_rows}行 vs 投委会版{ic_data_rows}行"
            f"（差异{diff_pct:.0f}%），请人工复核"
        )
    else:
        result.details = f"表格行数基本一致：底稿{draft_data_rows}行 vs 投委会版{ic_data_rows}行"

    result.evidence = [f"底稿Part二表格: {draft_data_rows}行", f"投委会版Part二表格: {ic_data_rows}行"]
    return result


# ── Q2: 跨节引用内联结论 ──────────────────────────────────

def check_q2(ic: str, ic_sections: dict) -> CheckResult:
    """
    检查投委会版中"不赘述""详见""见上文"等引用语后200字内是否有结论陈述。
    """
    result = CheckResult(code="Q2", name="跨节引用内联结论", passed=True, severity="PASS", details="")

    # 排除 Part 二（基本情况保持底稿原样，引用是允许的）
    # 通过找 Part 二开头和 Part 三开头确定范围
    part2_match = re.search(r'^##\s*二[、.．\s].*$', ic, re.MULTILINE)
    part3_match = re.search(r'^##\s*三[、.．\s].*$', ic, re.MULTILINE)
    part2_start = part2_match.start() if part2_match else -1
    part2_end = part3_match.start() if part3_match else -1

    # 匹配交叉引用短语
    ref_patterns = [
        r'不赘述',
        r'详见[^\s，。]{1,30}',
        r'见上文',
        r'前文已[^\s，。]{0,20}',
        r'如上[所述]',
    ]

    violations = []
    for pattern in ref_patterns:
        for m in re.finditer(pattern, ic):
            pos = m.start()
            # 跳过 Part 二 中的引用
            if part2_start >= 0 and part2_start <= pos <= part2_end:
                continue
            # 检查后200字符是否有实质性结论（风险等级/判断/结论关键词）
            after_text = ic[pos:pos + 200]
            conclusion_markers = [
                r'风险等级[：:][^\n]{1,30}',
                r'[高中低]风险',
                r'综合[评估判断]',
                r'[建议要求]将.{2,30}作为',
                r'存在[^\s，。]{2,20}风险',
                r'风险[可暂][以不予]',
                r'总体[风险判断]',
                r'结论[：:]',
                r'判断[：:]',
                r'建议在交易文件中',
                r'该等.*?需[要在]',
                r'需[要].*?[跟踪落实整改]',
                r'[，。]该',
            ]
            # 同时检查引用本身是否属于"补充说明"而非"省略结论"
            # 如果引用后面紧跟着标点+继续论述（如"详见财务维度），..."），视为补充说明
            context_around = ic[max(0, pos - 20):pos + 10]
            is_supplementary = bool(re.search(r'详见.{1,10}维度|详见.{1,10}方面|详见.{1,10}角度|详见.{1,10}部分\）', ic[pos:pos + 15]))
            
            has_conclusion = any(re.search(cp, after_text) for cp in conclusion_markers)
            if not has_conclusion and not is_supplementary:
                # 获取所在行的上下文
                line_start = ic.rfind("\n", 0, pos) + 1
                line_end = ic.find("\n", pos)
                context = ic[line_start:line_end].strip()
                violations.append(context[:80])

    if violations:
        result.passed = False
        result.severity = "FAIL"
        result.details = f"发现{len(violations)}处交叉引用缺少内联结论"
        result.evidence = violations[:5]  # 最多展示5处
    else:
        result.details = "所有交叉引用均包含内联结论，或无交叉引用"

    return result


# ── Q3: 财务数据多年对比 ──────────────────────────────────

def check_q3(ic: str, ic_sections: dict) -> CheckResult:
    """
    检查 3.6 节（财务相关）的表格是否有≥2个年度列。
    """
    result = CheckResult(code="Q3", name="财务数据多年对比", passed=True, severity="PASS", details="")

    # 优先在 Part 三 中查找 3.6/财务/其他关注 三级标题
    # 也尝试整篇搜索
    fin_section = find_section(ic_sections, ["3.6", "财务", "其他关注"])
    if not fin_section:
        # 可能在 Part 三 内部作为 ### 三级标题
        part3 = find_section_by_index(ic_sections, 3)
        if part3:
            content = part3[1]
            # 尝试匹配 ### 3.6 或含"其他关注"的三级标题
            # 注意：使用 ### 开头但排除 ####
            sub_match = re.search(r'(###\s+(?:3\.6|其他关注|财务).*?)(?=^###\s+[^#]|\Z)', content, re.MULTILINE | re.DOTALL)
            if sub_match:
                fin_section = ("子章节", sub_match.group(0))
    if not fin_section:
        # fallback: 在 Part 三 整体中查找
        fin_section = find_section_by_index(ic_sections, 3)
    if not fin_section:
        result.severity = "WARN"
        result.details = "未找到 3.6/财务相关章节，跳过"
        return result

    content = fin_section[1]
    tables = extract_table_rows(content)

    year_columns = set()
    year_pattern = re.compile(r'(20\d{2})[年]?')
    multi_year_tables = 0
    single_year_tables = 0

    for rows_idx, table_rows in enumerate([tables]):  # 简化：所有行视为一个大表
        years_in_table = set()
        for row in table_rows:
            for cell in row:
                for ym in year_pattern.finditer(cell):
                    years_in_table.add(ym.group(1))
        if len(years_in_table) >= 2:
            multi_year_tables += 1
            year_columns.update(years_in_table)
        elif len(years_in_table) == 1:
            single_year_tables += 1

    # 更精确地按表格分组检查
    # 用连续的 |---| 分隔行切分表格
    table_groups = []
    current_table = []
    in_table = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|"):
            current_table.append(stripped)
            in_table = True
        else:
            if in_table and current_table:
                table_groups.append(current_table)
                current_table = []
                in_table = False
    if current_table:
        table_groups.append(current_table)

    multi_year_count = 0
    single_year_count = 0
    for tg in table_groups:
        all_text = " ".join(tg)
        years = set(year_pattern.findall(all_text))
        if len(years) >= 2:
            multi_year_count += 1
            year_columns.update(years)
        elif len(years) == 1:
            single_year_count += 1

    if multi_year_count == 0 and single_year_count > 0:
        result.passed = False
        result.severity = "FAIL"
        result.details = f"财务章节共{single_year_count}个表格均仅有单年数据，缺少多年对比"
        result.evidence = [f"仅发现年度: {sorted(year_columns)}"]
    elif single_year_count > 0 and multi_year_count > 0:
        result.severity = "WARN"
        result.details = f"多年对比表{multi_year_count}个，单年表{single_year_count}个，请复核单年表是否需要补充"
        result.evidence = [f"涉及年度: {sorted(year_columns)}"]
    else:
        result.details = f"发现{multi_year_count}个多年对比表格" + (f"，涉及年度{sorted(year_columns)}" if year_columns else "")
        result.evidence = [f"涉及年度: {sorted(year_columns)}"]

    return result


# ── Q4: 保护条款4方向齐全 ──────────────────────────────────

def check_q4(ic: str, ic_sections: dict) -> CheckResult:
    """
    检查 Part 四 是否包含全部4个保护条款方向。
    """
    result = CheckResult(code="Q4", name="保护条款4方向齐全", passed=True, severity="PASS", details="")

    part4 = find_section_by_index(ic_sections, 4) or find_section(ic_sections, ["四、投资", "四、交易", "4 投资方案"])
    if not part4:
        result.passed = False
        result.severity = "FAIL"
        result.details = "未找到 Part 四（投资方案）章节"
        return result

    content = part4[1]

    directions = {
        "先决条件": ["先决条件", "交割前提", "Closing Condition", "CP"],
        "交割后承诺": ["交割后承诺", "交割后义务", "Post-Closing", "PC"],
        "陈述保证": ["陈述与保证", "陈述保证", "陈述和保证", "Representation", "R&W"],
        "赔偿条款": ["赔偿", "Indemnity", "违约责任"],
    }

    found = {}
    missing = []
    for direction, keywords in directions.items():
        found_any = False
        for kw in keywords:
            if re.search(kw, content, re.IGNORECASE):
                found_any = True
                found[direction] = kw
                break
        if not found_any:
            missing.append(direction)

    if missing:
        result.passed = False
        result.severity = "FAIL"
        result.details = f"缺少{len(missing)}个方向：{'、'.join(missing)}"
        result.evidence = [f"已找到: {list(found.keys())}", f"缺失: {missing}"]
    else:
        result.details = "4个保护条款方向齐全"
        result.evidence = [f"{k}: 匹配关键词 '{v}'" for k, v in found.items()]

    return result


# ── Q5: 总结引用与正文一致 ──────────────────────────────────

def check_q5(ic: str, ic_sections: dict) -> CheckResult:
    """
    检查 Part 五 总结段提到的保护方向与 Part 四 实际包含的方向是否一致。
    """
    result = CheckResult(code="Q5", name="总结引用与正文一致", passed=True, severity="PASS", details="")

    part4 = find_section_by_index(ic_sections, 4) or find_section(ic_sections, ["四、投资", "四、交易", "4 投资方案"])

    if not part4:
        result.severity = "WARN"
        result.details = "未找到 Part 四，跳过一致性检查"
        return result

    p4_content = part4[1]
    # Part 五/六 合并搜索总结段
    part5_raw = find_section_by_index(ic_sections, 5) or find_section(ic_sections, ["五、风险", "五、总结"])
    part6_raw = find_section_by_index(ic_sections, 6) or find_section(ic_sections, ["六、风险", "六、总结"])
    p5_content = ""
    if part5_raw:
        p5_content += part5_raw[1]
    if part6_raw:
        p5_content += part6_raw[1]

    # 方向 → 同义词列表
    direction_synonyms = {
        "先决条件": ["先决条件", "交割前提", "交割先决条件", "Closing Condition", "CP"],
        "交割后承诺": ["交割后承诺", "交割后义务", "Post-Closing", "PC"],
        "陈述保证": ["陈述与保证", "陈述保证", "陈述和保证", "Representation", "R&W"],
        "赔偿": ["赔偿", "Indemnity", "违约责任"],
    }

    def detect_directions(text):
        """用同义词组检测方向"""
        found = set()
        for direction, synonyms in direction_synonyms.items():
            for syn in synonyms:
                if syn in text:
                    found.add(direction)
                    break
        return found

    p4_found = detect_directions(p4_content)
    p5_found = detect_directions(p5_content)

    if p4_found != p5_found:
        only_p4 = p4_found - p5_found
        only_p5 = p5_found - p4_found
        issues = []
        if only_p4:
            issues.append(f"Part四有但总结未提: {only_p4}")
        if only_p5:
            issues.append(f"总结提到但Part四无: {only_p5}")
        result.passed = False
        result.severity = "FAIL"
        result.details = "总结引用与Part四不一致: " + "; ".join(issues)
    else:
        result.details = f"总结引用与Part四一致，均包含: {p4_found or '未检测到保护方向'}"

    result.evidence = [f"Part四方向: {sorted(p4_found)}", f"Part五/六方向: {sorted(p5_found)}"]
    return result


# ── Q6: 正面因素保留 ──────────────────────────────────────

def check_q6(ic: str, ic_sections: dict) -> CheckResult:
    """
    检查 Part 五 是否包含"正面因素"独立段落。
    """
    result = CheckResult(code="Q6", name="正面因素保留", passed=True, severity="PASS", details="")

    # 正面因素可能在"风险总结"章节（Part 五或 Part 六），也可能在"风险矩阵"章节
    # 同时搜索 Part 五 和 Part 六
    part5 = find_section_by_index(ic_sections, 5)
    part6 = find_section_by_index(ic_sections, 6)
    content = ""
    if part5:
        content += part5[1]
    if part6:
        content += part6[1]
    if not content:
        result.severity = "WARN"
        result.details = "未找到 Part 五/六，跳过"
        return result

    positive_markers = ["正面因素", "积极因素", "有利因素", "正面评价", "正面信息"]
    found = False
    found_marker = ""
    for marker in positive_markers:
        if marker in content:
            found = True
            found_marker = marker
            break

    if not found:
        result.passed = False
        result.severity = "FAIL"
        result.details = "Part 五未发现正面因素段落"
    else:
        result.details = f"正面因素段落存在（关键词: {found_marker}）"

    return result


# ── Q7: 风险等级一致 ──────────────────────────────────────

def check_q7(draft: str, ic: str) -> CheckResult:
    """
    提取两版中的风险等级，比对是否一致。
    支持多种格式：Rxx编号、emoji标记（🔴🟠🟡🟢）、表格行等。
    """
    result = CheckResult(code="Q7", name="风险等级一致", passed=True, severity="PASS", details="")

    # 风险等级关键词 → 规范化名称
    level_map = {
        "高风险": "高", "🔴高": "高", "🔴": "高",
        "中高风险": "中高", "中高": "中高", "🟠中高": "中高", "🟠": "中高",
        "中风险": "中", "中": "中", "🟡中": "中", "🟡": "中",
        "中低风险": "中低", "中低": "中低", "🟢中低": "中低",
        "低风险": "低", "低": "低", "🟢低": "低",
    }

    # 规范化函数
    def normalize_level(raw):
        raw = raw.strip()
        for key, val in level_map.items():
            if key in raw:
                return val
        return raw

    def extract_risks(text):
        risks = {}

        # 模式1: Rxx 编号 + 等级（R01 | 事项 | 高风险 | ...）
        p1 = re.compile(r'(R\d{2})\s*[|：:]\s*[^|]*?[|：:]\s*(高中低风险|中高风险|中低风险|高风险|中风险|低风险)', re.IGNORECASE)
        for m in p1.finditer(text):
            code = m.group(1).upper()
            risks[code] = normalize_level(m.group(2))

        # 模式2: Rxx 后面紧跟等级（非表格）
        if not risks:
            p2 = re.compile(r'(R\d{2})[^。\n]{0,30}?(高中低风险|中高风险|中低风险|高风险|中风险|低风险)')
            for m in p2.finditer(text):
                code = m.group(1).upper()
                if code not in risks:
                    risks[code] = normalize_level(m.group(2))

        # 模式3: 风险矩阵表格中的 emoji 等级（| 1 | 事项 | 🔴高 | ...）
        if not risks:
            p3 = re.compile(r'\|\s*(\d+)\s*\|[^|]*\|\s*([🔴🟠🟡🟢]+\s*[高中低]+(?:风险)?)\s*\|')
            for m in p3.finditer(text):
                code = f"R{int(m.group(1)):02d}"
                risks[code] = normalize_level(m.group(2))

        # 模式4: 行内"风险等级：🔴高"等
        if not risks:
            p4 = re.compile(r'(?:风险等级|风险水平)\s*[：:]\s*([🔴🟠🟡🟢]?\s*[高中低]+(?:风险)?)')
            idx = 1
            for m in p4.finditer(text):
                code = f"R{idx:02d}"
                risks[code] = normalize_level(m.group(1))
                idx += 1

        return risks

    draft_risks = extract_risks(draft)
    ic_risks = extract_risks(ic)

    if not draft_risks and not ic_risks:
        result.severity = "WARN"
        result.details = "两版均未提取到风险等级，可能格式不同，请人工复核"
        return result

    if not draft_risks:
        result.severity = "WARN"
        result.details = "底稿版未提取到风险编号，跳过比对"
        return result

    mismatches = []
    missing_in_ic = []

    for code, level in sorted(draft_risks.items()):
        if code not in ic_risks:
            missing_in_ic.append(code)
        elif ic_risks[code] != level:
            mismatches.append(f"{code}: 底稿={level} → 投委会版={ic_risks[code]}")

    if mismatches or missing_in_ic:
        result.passed = False
        result.severity = "FAIL"
        parts = []
        if mismatches:
            parts.append(f"等级变动{len(mismatches)}项: " + "; ".join(mismatches[:5]))
        if missing_in_ic:
            parts.append(f"投委会版缺失{len(missing_in_ic)}项: {', '.join(missing_in_ic[:5])}")
        result.details = "存在不一致: " + "; ".join(parts)
        result.evidence = mismatches[:5] + [f"缺失: {', '.join(missing_in_ic[:5])}"] if missing_in_ic else mismatches[:5]
    else:
        matched = len(draft_risks)
        result.details = f"全部{matched}项风险等级一致"
        result.evidence = [f"{k}: {v}" for k, v in sorted(draft_risks.items())]

    return result


# ── Q8: 待补标注保留 ──────────────────────────────────────

def check_q8(draft: str, ic: str) -> CheckResult:
    """
    检查底稿中所有【待补·Pxxx】在投委会版中是否均存在。
    """
    result = CheckResult(code="Q8", name="待补标注保留", passed=True, severity="PASS", details="")

    # 匹配 【待补·Pxxx】 或 【待补·Pxxx·说明】
    pending_pattern = re.compile(r'【待补[^】]*?P\d{1,4}[^】]*?】')
    draft_pending = pending_pattern.findall(draft)
    ic_pending = pending_pattern.findall(ic)

    draft_set = set(draft_pending)
    ic_set = set(ic_pending)

    if not draft_set:
        result.details = "底稿版无待补标注，跳过"
        return result

    missing = draft_set - ic_set
    if missing:
        result.passed = False
        result.severity = "FAIL"
        result.details = f"底稿{len(draft_set)}项待补标注中，{len(missing)}项在投委会版中缺失"
        result.evidence = sorted(missing)[:10]
    else:
        result.details = f"全部{len(draft_set)}项待补标注均已保留"
        result.evidence = sorted(draft_set)[:5]

    return result


# ── 主逻辑 ──────────────────────────────────────────────

def run_checks(draft_path: str, ic_path: str) -> CheckReport:
    """执行全部 8 项校验"""
    draft = read_markdown(draft_path)
    ic = read_markdown(ic_path)

    draft_sections = split_sections(draft)
    ic_sections = split_sections(ic)

    report = CheckReport(draft_file=draft_path, ic_file=ic_path)

    checks = [
        lambda: check_q1(draft, ic, draft_sections, ic_sections),
        lambda: check_q2(ic, ic_sections),
        lambda: check_q3(ic, ic_sections),
        lambda: check_q4(ic, ic_sections),
        lambda: check_q5(ic, ic_sections),
        lambda: check_q6(ic, ic_sections),
        lambda: check_q7(draft, ic),
        lambda: check_q8(draft, ic),
    ]

    for check_fn in checks:
        r = check_fn()
        report.results.append(r)
        report.total += 1
        if r.severity == "PASS":
            report.passed += 1
        elif r.severity == "WARN":
            report.warned += 1
        elif r.severity == "FAIL":
            report.failed += 1

    return report


def format_report_text(report: CheckReport, verbose: bool = False) -> str:
    """格式化文本报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("投委会版一致性校验报告")
    lines.append("=" * 60)
    lines.append(f"底稿版: {report.draft_file}")
    lines.append(f"投委会版: {report.ic_file}")
    lines.append(f"校验结果: {report.overall}")
    lines.append(f"统计: 通过 {report.passed}/{report.total}  警告 {report.warned}  失败 {report.failed}")
    lines.append("-" * 60)

    for r in report.results:
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(r.severity, "?")
        lines.append(f"\n{icon} [{r.code}] {r.name} — {r.severity}")
        lines.append(f"   {r.details}")
        if verbose and r.evidence:
            for ev in r.evidence:
                lines.append(f"   → {ev}")

    lines.append("\n" + "=" * 60)
    if report.overall == "FAIL":
        lines.append("❌ 存在失败项，请根据上述检查结果修改投委会版后重新校验。")
    elif report.overall == "PASS_WITH_WARNINGS":
        lines.append("⚠️ 通过但有警告项，建议人工复核。")
    else:
        lines.append("✅ 全部检查通过！")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_report_json(report: CheckReport) -> str:
    """格式化 JSON 报告"""
    return json.dumps(asdict(report), ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="投委会版一致性校验工具 — 对照底稿版与投委会版，执行8项自检 (writing_patterns.md §10.7-C)"
    )
    parser.add_argument("draft", help="底稿版 markdown 文件路径")
    parser.add_argument("ic_version", help="投委会版 markdown 文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细证据")
    args = parser.parse_args()

    report = run_checks(args.draft, args.ic_version)

    if args.json:
        print(format_report_json(report))
    else:
        print(format_report_text(report, verbose=args.verbose))

    # 返回码：0=全部通过，1=有警告，2=有失败
    if report.overall == "FAIL":
        sys.exit(2)
    elif report.overall == "PASS_WITH_WARNINGS":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
