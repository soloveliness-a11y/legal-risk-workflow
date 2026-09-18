#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交付验收脚本（validate_delivery.py）

Mechanical preflight validator for CONTRACT acceptance checks.
Covers: AC2 coverage, AC4 cross-document consistency (risk_id/company/date),
schema validation, AC5 absolute-phrase scan.
Does NOT cover: AC1 zero-loss comparison, AC3 deep provenance, AC4 amount consistency.
These require human judgment.

用途：对单个项目目录下的全部产出跑 CONTRACT.md §6 验收契约中可脚本化判定的检查项，
输出 PASS / WARN / FAIL 三级结论（WARN = 机械检查无法终判、需人工判读项）
及 MANUAL 人工核验提示（机械检查未覆盖项，不计数、不影响退出码）。

检查项：
  必须产物       Phase 声明 completed 但缺 CONTRACT §6 必须产物 → FAIL
                 （验收不过=交付不成立）；Phase 未执行 / status != completed → SKIP
  AC2 覆盖度     risk_matrix.json 每条 risk_id 在报告正文出现（双向，无孤儿）；
                 条款落实表中每条 risk_id ≥1 条款映射（显式"无法映射"清单除外）
  AC3 来源标注   报告正文抽样 N 个数字/百分比/金额表述，检查所在行是否带
                 来源/确定性标记（WARN 级，人工判读）
  AC4 跨文档一致 risk_id / 公司名 / 日期 在 矩阵/正文/落实表/台账 间一致；
                 金额一致性不在机械范围（regex 比对脆弱），逐 Phase 输出 MANUAL 提示
  Schema 校验    output.json 必填 6 字段；确定性标签合法枚举（CONTRACT §2.3）；
                 risk_matrix.json 必填字段
  AC5 降级显式化 绝对性表述（"无风险"等）附近是否有来源标注或降级声明（WARN 级）

与 scripts/tools/consistency_checker.py 共存：后者专注报告分章内部一致性
（风险等级跨章、内部字段泄漏），本脚本为 AC 验收统一入口，不重复其检查。

用法：
  python3 scripts/validate_delivery.py projects/{项目名}/
  python3 scripts/validate_delivery.py projects/{项目名}/ --phase 04_risk_report
  python3 scripts/validate_delivery.py projects/{项目名}/ --verbose --sample 30

  --phase  限定检查范围（只检查该 Phase 目录的产出及以其为下游的检查）
  --verbose 输出 PASS 项细节（样本行、文件清单等）
  --sample  AC3 抽样上限，默认 20

退出码：0 = 全部 PASS/WARN；1 = 存在 FAIL；2 = 用法/目录错误。
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────────────

PHASES = ["01_dd_prep", "02_dd_check", "03_dd_interview", "04_risk_report",
          "05_report_review", "06_txn_docs", "07_post_invest"]

# 必须产物清单（CONTRACT §6：Phase 声明 completed 而缺任一 → FAIL，验收不过=交付不成立；
# Phase 未执行 / status != completed → SKIP）。02/03 为中间核查环节，无对外必须产物。
# patterns=None 表示复用 find_report 的报告正文发现规则（分章优先→最新完整报告→兜底）。
REQUIRED_ARTIFACT_PATTERNS: dict[str, list[tuple[str, tuple[str, ...] | None]]] = {
    "01_dd_prep": [("risk_hypotheses.md", ("risk_hypotheses*.md",)),
                   ("checklist_external.md", ("checklist_external*.md",))],
    "04_risk_report": [("报告正文", None),
                       ("risk_matrix.json", ("risk_matrix.json",))],
    "05_report_review": [("复核意见 md", ("*复核*.md", "*review*.md"))],
    "06_txn_docs": [("条款落实表", ("*落实表*.md",)),
                    ("覆盖度报告", ("*覆盖度*.md",))],
    "07_post_invest": [("台账 md", ("*台账*.md",))],
}

# AC4 金额一致性不在机械检查范围（regex 比对脆弱、误判代价高）：
# 每个相关 Phase 输出一行 MANUAL 提示，由人工核验
AC4_AMOUNT_PHASES = ("04_risk_report", "06_txn_docs", "07_post_invest")

# risk_id 提取：R+2~3位数字；前后不得紧邻 ASCII 字母数字（兼容中文紧邻场景，
# 如"：R01""项R02"，\b 对 CJK 无效故不用）
RISK_ID_RE = re.compile(r"(?<![A-Za-z0-9])R(\d{2,3})(?![0-9])")

# output.json 最小 schema（CONTRACT §3）
OUTPUT_REQUIRED_FIELDS = ["skill", "version", "project", "date", "status", "outputs"]
OUTPUT_STATUS_ENUM = {"completed", "partial", "blocked"}
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# 确定性标签合法枚举（CONTRACT §2.3，全库唯一定义，禁止另造）
CERTAINTY_LABELS = ["✅已确认", "📌待核实", "⚠️不一致", "❌未提供", "[BP声称]", "[推断]"]
CERTAINTY_STARTS = ["已确认", "待核实", "不一致", "未提供"]
# emoji 后首字命中这些才视为"疑似想写确定性标签"（过滤 ⚠️需关注 类装饰性用法）
LABEL_LIKE_STARTS = set(c[0] for c in CERTAINTY_STARTS)
# emoji 后直接紧贴的 1-6 个汉字（用于发现"✅已核实"类变体）
EMOJI_LABEL_RE = re.compile(r"(⚠️|✅|📌|❌)([\u4e00-\u9fff]{1,6})")
BRACKET_LABEL_RE = re.compile(r"\[([^\]\n]{1,12})\]")
BRACKET_HINT_KEYS = ("声称", "推断", "已确认", "待核实")

# AC3：数字/百分比/金额表述模式
AMOUNT_RE = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:万元|亿元|万美元|亿|万|元)")
PCT_RE = re.compile(r"\d[\d,]*(?:\.\d+)?\s*%")
COUNT_RE = re.compile(r"\d{3,}[\d,]*\s*(?:股|人|家|名|笔)")

# AC3：来源/确定性标记（命中其一即视为该行有标注）。
# 注意：不含裸"核查/核验/核对"——"经核查"既非来源也非降级声明，不得放行
SOURCE_MARKER_RE = re.compile(
    r"来源|source|Source|Dossier|dossier|qcc|QCC|CLI|verification_table|interview_result|"
    r"访谈|工商|三方报告|尽调|检索|底稿|披露函|建议书|memo|Memo|"
    r"✅|📌|⚠️|❌|🔴|🟠|🟡|🔵|🟢|\[BP声称\]|\[推断\]")

# AC5：绝对性表述 + 降级/来源标记
ABSOLUTE_PHRASES = ["无风险", "未发现风险", "不存在风险", "没有风险", "不涉及风险",
                    "零风险", "无重大风险", "未发现重大风险", "不存在重大风险"]
DEGRADE_MARKER_RE = re.compile(
    r"来源|source|Dossier|未核查|待核实|未提供|未取得|未披露|✅|📌|⚠️|❌|\[推断\]|\[BP声称\]|"
    r"检索|尽调|访谈|工商|CLI|qcc|AC5|不排除|无法完全排除|审慎口径")

# 报告正文发现规则（与 consistency_checker 口径一致：分章优先，其次最新完整报告）
CHAPTER_GLOB = "report_ch*.md"
FULL_REPORT_KEYWORD = "风控报告"
FULL_REPORT_EXCLUDE = "投委会版"
# 完整报告关键词未命中时的兜底：04 目录下最新的非辅助文件（覆盖"核查清单"等命名变体）
AUX_FILE_RE = re.compile(r"output|pending|selfcheck|self_check|consistency|analysis_log|^report_ch", re.I)

# 日期解析（用于 AC4 日期一致性）
DATE_VALUE_RE = re.compile(r"(\d{4})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})")
DATE_SPAN_WARN_DAYS = 30


# ── 结果收集 ──────────────────────────────────────────────────────────

class Reporter:
    """收集并即时打印 PASS/WARN/FAIL；WARN/FAIL 恒出细节，PASS 细节仅 --verbose"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.counts = {"PASS": 0, "WARN": 0, "FAIL": 0}

    def emit(self, level: str, tag: str, msg: str, details: list[str] | None = None):
        self.counts[level] += 1
        print(f"{level} {tag}: {msg}")
        if details:
            if level == "PASS" and not self.verbose:
                return
            for d in details:
                print(f"  {d}")

    def warn_skip(self, what: str, reason: str):
        self.emit("WARN", "SKIP", f"{what} 跳过——{reason}")

    def manual(self, tag: str, msg: str):
        """MANUAL 提示行：机械检查未覆盖、需人工完成的项；不计数、不影响退出码"""
        print(f"MANUAL {tag}: {msg}")


# ── 基础工具 ──────────────────────────────────────────────────────────

def read_text(path: Path) -> tuple[str | None, str | None]:
    """读文本；返回 (内容, 错误信息)，两者互斥"""
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, str(exc)


def load_json(path: Path) -> tuple[object | None, str | None]:
    """读 JSON；返回 (对象, 错误信息)"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except OSError as exc:
        return None, f"读取失败：{exc}"
    except json.JSONDecodeError as exc:
        return None, f"JSON 解析失败：{exc}"


def extract_risk_ids(text: str) -> set[int]:
    """提取文本中的 risk_id 编号集合（归一化为 int，兼容 R02/R13 复合写法）"""
    return {int(m.group(1)) for m in RISK_ID_RE.finditer(text)}


def fmt_rid(n: int) -> str:
    return f"R{n:02d}"


def snippet(line: str, pos: int, width: int = 56) -> str:
    """以 pos 为中心截取行片段，超长加省略号"""
    start = max(0, pos - width // 2)
    end = min(len(line), pos + width // 2)
    frag = line[start:end].strip()
    if start > 0:
        frag = "…" + frag
    if end < len(line):
        frag = frag + "…"
    return frag.replace("\t", " ")


def iter_lines(text: str) -> list[tuple[int, str]]:
    return list(enumerate(text.splitlines(), start=1))


# ── 产出定位 ──────────────────────────────────────────────────────────

def find_report(report_dir: Path) -> list[tuple[str, str]]:
    """定位报告正文：report_ch*.md 分章优先；否则取最新 *风控报告*.md（排除投委会版）"""
    if not report_dir.is_dir():
        return []
    chapters = sorted(report_dir.glob(CHAPTER_GLOB))
    if chapters:
        out = []
        for p in chapters:
            text, _ = read_text(p)
            if text is not None:
                out.append((p.name, text))
        if out:
            return out
    fulls = [p for p in report_dir.glob(f"*{FULL_REPORT_KEYWORD}*.md")
             if FULL_REPORT_EXCLUDE not in p.name]
    if not fulls:
        # 兜底：目录下最新 md（排除辅助文件），覆盖"核查清单"等报告命名变体
        fulls = [p for p in report_dir.glob("*.md") if not AUX_FILE_RE.search(p.stem)]
    fulls.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if fulls:
        text, _ = read_text(fulls[0])
        if text is not None:
            return [(fulls[0].name, text)]
    return []


# ── Schema 检查 ───────────────────────────────────────────────────────

def check_output_json(rep: Reporter, project_dir: Path, scope: list[str]):
    """output.json：必填 6 字段 + status/date 枚举校验"""
    checked, passed = 0, 0
    for phase in scope:
        phase_dir = project_dir / phase
        if not phase_dir.is_dir():
            continue
        opath = phase_dir / "output.json"
        if not opath.exists():
            rep.warn_skip(f"{phase}/output.json", "Phase 目录存在但无状态文件（CONTRACT §3 要求每次执行产出）")
            continue
        checked += 1
        data, err = load_json(opath)
        if err or not isinstance(data, dict):
            rep.emit("FAIL", "Schema", f"{phase}/output.json 无法解析（{err}）")
            continue
        problems = [f"缺必填字段 {f}" for f in OUTPUT_REQUIRED_FIELDS if f not in data]
        status = data.get("status")
        if status is not None and status not in OUTPUT_STATUS_ENUM:
            problems.append(f"status={status!r} 不在枚举 {sorted(OUTPUT_STATUS_ENUM)}")
        date = data.get("date")
        if date is not None and not (isinstance(date, str) and ISO_DATE_RE.match(date)):
            problems.append(f"date={date!r} 非 ISO 日期（YYYY-MM-DD）")
        outs = data.get("outputs")
        if outs is not None and (not isinstance(outs, list) or not outs):
            problems.append("outputs 须为非空列表")
        if problems:
            rep.emit("FAIL", "Schema", f"{phase}/output.json 校验未通过", problems)
        else:
            passed += 1
            rep.emit("PASS", "Schema", f"output.json 字段完整（{phase}）",
                     [f"skill={data.get('skill')} version={data.get('version')} status={status}"])
    if checked == 0:
        rep.warn_skip("output.json 检查", "范围内无任何 Phase 目录含 output.json")
    elif passed == checked:
        rep.emit("PASS", "Schema", f"output.json 字段完整 ({passed}/{checked} 个 Phase 状态文件)")


# ── 必须产物检查（CONTRACT §6 验收语义）──────────────────────────────

def check_required_artifacts(rep: Reporter, project_dir: Path, scope: list[str]):
    """Phase 声明 completed 但缺必须产物 → FAIL（验收不过=交付不成立）；
    Phase 目录不存在 / output.json 缺失或不可解析 / status != completed → SKIP（交付尚未
    主张完成，不判 FAIL）。"""
    for phase in scope:
        if phase not in REQUIRED_ARTIFACT_PATTERNS:
            continue
        phase_dir = project_dir / phase
        if not phase_dir.is_dir():
            continue  # Phase 未执行 → SKIP
        opath = phase_dir / "output.json"
        if not opath.exists():
            rep.warn_skip(f"{phase} 必须产物检查", "无 output.json，无法确认是否 completed")
            continue
        data, err = load_json(opath)
        if err or not isinstance(data, dict):
            rep.warn_skip(f"{phase} 必须产物检查", f"output.json 无法解析（{err}）")
            continue
        status = data.get("status")
        if status != "completed":
            rep.warn_skip(f"{phase} 必须产物检查", f"status={status!r}（未主张完成，不判 FAIL）")
            continue
        missing, present = [], []
        for label, patterns in REQUIRED_ARTIFACT_PATTERNS[phase]:
            if patterns is None:
                names = [name for name, _ in find_report(phase_dir)]
            else:
                names = sorted({p.name for pat in patterns for p in phase_dir.glob(pat)})
            if names:
                present.append(f"{label}: {', '.join(names)}")
            else:
                missing.append(label)
        if missing:
            rep.emit("FAIL", "Artifacts",
                     f"{phase} 声明 completed 但缺必须产物（CONTRACT §6：验收不过=交付不成立）",
                     [f"缺失：{m}" for m in missing] + [f"具备：{p}" for p in present])
        else:
            rep.emit("PASS", "Artifacts", f"{phase} 必须产物齐全（status=completed）", present)


def check_risk_matrix_schema(rep: Reporter, matrix: dict | None, matrix_path: Path) -> bool:
    """risk_matrix.json 结构校验；通过返回 True"""
    if matrix is None:
        return False
    risks = matrix.get("risks")
    if not isinstance(risks, list) or not risks:
        rep.emit("FAIL", "Schema", f"{matrix_path.name} 缺少非空 risks 列表")
        return False
    problems, seen = [], set()
    for i, r in enumerate(risks, start=1):
        if not isinstance(r, dict):
            problems.append(f"第 {i} 条不是对象")
            continue
        rid = r.get("risk_id", r.get("id"))
        if not rid:
            problems.append(f"第 {i} 条缺 risk_id")
        elif not (isinstance(rid, str) and re.fullmatch(r"R\d{2,3}", rid)):
            problems.append(f"第 {i} 条 risk_id={rid!r} 不符合 R+两位数字 格式")
        elif rid in seen:
            problems.append(f"risk_id={rid} 重复出现")
        else:
            seen.add(rid)
        if not (r.get("risk_description") or r.get("description") or r.get("title")):
            problems.append(f"第 {i} 条缺 risk_description")
        if not (r.get("risk_level") or r.get("level")):
            problems.append(f"第 {i} 条缺 risk_level")
    if problems:
        rep.emit("FAIL", "Schema", f"{matrix_path.name} 必填字段校验未通过", problems)
        return False
    rep.emit("PASS", "Schema", f"{matrix_path.name} 必填字段完整 ({len(risks)} 条)")
    return True


def _certainty_value_ok(v: str) -> bool:
    return v.strip() in CERTAINTY_LABELS or any(v.strip().startswith(c) for c in CERTAINTY_LABELS)


def _walk_json_certainty(obj, out: list[tuple[str, str]], path: str = "$"):
    """递归找 certainty/确定性 字段"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("certainty", "确定性") and isinstance(v, str):
                out.append((f"{path}.{k}", v))
            _walk_json_certainty(v, out, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_json_certainty(v, out, f"{path}[{i}]")


def check_certainty_labels(rep: Reporter, project_dir: Path, scope: list[str]):
    """确定性标签枚举校验（CONTRACT §2.3）。范围：Dossier + 02/03 内部产出（对外报告不扫，
    其内部的 ✅ 简写属合法用法，由 consistency_checker 的内部字段泄漏检查管辖）"""
    targets: list[tuple[str, str]] = []  # (显示名, 文本)
    dossier, _ = read_text(project_dir / "project_dossier.md")
    if dossier:
        targets.append(("project_dossier.md", dossier))
    for phase in ("02_dd_check", "03_dd_interview"):
        if phase not in scope:
            continue
        pdir = project_dir / phase
        if not pdir.is_dir():
            continue
        for p in sorted(list(pdir.glob("*.json")) + list(pdir.glob("*.md"))):
            text, _ = read_text(p)
            if text is not None:
                targets.append((f"{phase}/{p.name}", text))

    if not targets:
        rep.warn_skip("确定性标签检查", "未找到 Dossier 或 02/03 内部产出")
        return

    md_variants, json_bad = [], []
    for name, text in targets:
        for lineno, line in iter_lines(text):
            for m in EMOJI_LABEL_RE.finditer(line):
                following = m.group(2)
                # 仅当首字像确定性标签（已/待/不/未）且不等于任一规范前缀时告警，
                # 过滤"⚠️需关注""📌列入现场"等装饰性 emoji 用法
                if (following[0] in LABEL_LIKE_STARTS
                        and not any(following.startswith(s) for s in CERTAINTY_STARTS)):
                    md_variants.append(f"{name}:L{lineno} \"{m.group(1)}{following}\"")
            for m in BRACKET_LABEL_RE.finditer(line):
                content = m.group(1)
                if any(k in content for k in BRACKET_HINT_KEYS) and content not in ("BP声称", "推断"):
                    md_variants.append(f"{name}:L{lineno} \"[{content}]\"")
        # JSON 文件内的 certainty 字段值校验
        if name.endswith(".json"):
            data, _ = load_json(Path(project_dir / name))
            if isinstance(data, (dict, list)):
                found: list[tuple[str, str]] = []
                _walk_json_certainty(data, found)
                for jp, v in found:
                    if not _certainty_value_ok(v):
                        json_bad.append(f"{name} {jp}={v!r}")

    if json_bad:
        rep.emit("FAIL", "Schema", f"certainty 字段值不在合法枚举（{len(json_bad)} 处）",
                 json_bad + [f"合法枚举：{' / '.join(CERTAINTY_LABELS)}"])
    if md_variants:
        rep.emit("WARN", "Schema", f"疑似非标准确定性标签变体 {len(md_variants)} 处（人工判读）",
                 md_variants + [f"合法枚举：{' / '.join(CERTAINTY_LABELS)}（CONTRACT §2.3）"])
    if not json_bad and not md_variants:
        rep.emit("PASS", "Schema", "确定性标签均在合法枚举内", [f"扫描范围：{len(targets)} 个文件"])


# ── AC2 覆盖度 ────────────────────────────────────────────────────────

def check_ac2_report(rep: Reporter, matrix_ids: set[int], report: list[tuple[str, str]]):
    """risk_matrix ↔ 报告正文 双向覆盖"""
    body_ids = set()
    for _, text in report:
        body_ids |= extract_risk_ids(text)
    if not matrix_ids:
        return  # 矩阵缺失已在加载处 WARN/FAIL
    missing = matrix_ids - body_ids
    orphans = body_ids - matrix_ids
    for n in sorted(missing):
        rep.emit("FAIL", "AC2", f"{fmt_rid(n)} 在 risk_matrix 中存在但正文未出现")
    for n in sorted(orphans):
        rep.emit("FAIL", "AC2", f"{fmt_rid(n)} 在正文出现但 risk_matrix 不存在（孤儿条目）")
    if not missing and not orphans:
        rep.emit("PASS", "AC2", f"报告正文与 risk_matrix 逐条对应，无孤儿条目 "
                 f"({len(matrix_ids)}/{len(matrix_ids)})")


def parse_txn_table(path: Path) -> tuple[set[int], set[int], str | None]:
    """解析落实表：返回 (已映射编号, 显式无法映射编号, 错误)。
    主表行 = 表格行首列 R 编号；含"未映射"标题之后的表格行计入显式无法映射。"""
    text, err = read_text(path)
    if text is None:
        return set(), set(), err
    mapped, unmapped = set(), set()
    in_unmapped_section = False
    for line in text.splitlines():
        if re.match(r"^#{1,4}\s", line) and "未映射" in line:
            in_unmapped_section = True
            continue
        m = re.match(r"^\|\s*(R\d{2,3})\s*\|", line.strip()) if not line.startswith("#") else None
        if m:
            (unmapped if in_unmapped_section else mapped).add(int(m.group(1)[1:]))
    return mapped, unmapped, None


def check_ac2_txn(rep: Reporter, matrix_ids: set[int], txn_dir: Path):
    """落实表覆盖度：每条 risk_id ≥1 条款映射（显式无法映射清单除外）"""
    tables = sorted(txn_dir.glob("*落实表*.md")) if txn_dir.is_dir() else []
    if not tables:
        rep.warn_skip("AC2 交易文件覆盖度", "06_txn_docs 未找到条款落实表（Phase 未执行或命名不符 *落实表*.md）")
        return
    mapped, unmapped = set(), set()
    for p in tables:
        m1, m2, err = parse_txn_table(p)
        if err:
            rep.warn_skip(f"落实表 {p.name}", err)
            continue
        mapped |= m1
        unmapped |= m2
        rep.emit("PASS", "AC2", f"落实表解析成功：{p.name}（映射 {len(m1)} 项）")
    missing = matrix_ids - mapped - unmapped
    for n in sorted(missing):
        rep.emit("FAIL", "AC2", f"{fmt_rid(n)} 在落实表中无任何条款映射（亦未列入无法映射清单）")
    silent_unmapped = unmapped - mapped  # 仅出现在无法映射清单
    if not missing:
        extra = f"，另 {len(silent_unmapped)} 项显式无法映射（合规）" if silent_unmapped else ""
        rep.emit("PASS", "AC2", f"落实表条款映射覆盖完整 "
                 f"({len(matrix_ids & mapped)}/{len(matrix_ids)}{extra})",
                 [f"落实表文件：{', '.join(p.name for p in tables)}"])
    # 覆盖度报告存在性（AC2 要求输出覆盖度报告）
    cov = sorted(txn_dir.glob("*覆盖度*.md")) if txn_dir.is_dir() else []
    if not cov:
        rep.warn_skip("覆盖度报告", "06_txn_docs 未找到 *覆盖度*.md（AC2 要求输出覆盖度报告）")


# ── AC3 来源标注抽样 ──────────────────────────────────────────────────

def _ac3_candidate_lines(text: str) -> list[tuple[int, str, int]]:
    """返回 (行号, 行, 首个匹配位置)；过滤空行/表格分隔线/纯标题行"""
    out = []
    for lineno, line in iter_lines(text):
        st = line.strip()
        if not st or re.fullmatch(r"[-|:\s]+", st) or (st.startswith("|") and "risk_id" in st):
            continue
        m = AMOUNT_RE.search(st) or PCT_RE.search(st) or COUNT_RE.search(st)
        if m:
            out.append((lineno, line, m.start()))
    return out


def check_ac3(rep: Reporter, report: list[tuple[str, str]], sample: int):
    """报告正文抽样：数字/百分比/金额表述所在行是否有来源标记（WARN 级）"""
    missing, total = [], 0
    for name, text in report:
        for lineno, line, pos in _ac3_candidate_lines(text):
            total += 1
            if not SOURCE_MARKER_RE.search(line):
                missing.append((name, lineno, line, pos))
    if total == 0:
        rep.warn_skip("AC3 来源标注抽样", "报告正文中未发现数字/百分比/金额表述")
        return
    shown = missing if len(missing) <= sample else missing[::max(1, len(missing) // sample)][:sample]
    details = [f"L{lineno}: \"{snippet(line, pos)}\"（{name}）" for name, lineno, line, pos in shown]
    if missing:
        rep.emit("WARN", "AC3",
                 f"{len(missing)}/{total} 处数字表述可能缺来源标注（人工判读）",
                 details + ([f"… 仅展示前 {sample} 处（--sample 可调）"] if len(missing) > sample else []))
    else:
        rep.emit("PASS", "AC3", f"抽样 {total} 处数字表述均带来源/确定性标记")


# ── AC4 跨文档一致性 ──────────────────────────────────────────────────

def _ledger_json_ids(data) -> set[int]:
    ids = set()
    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "risk_id" and isinstance(v, str):
                    ids.update(extract_risk_ids(v))
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
    walk(data)
    return ids


def check_ac4_risk_ids(rep: Reporter, matrix_ids: set[int], report: list[tuple[str, str]],
                       txn_dir: Path, post_dir: Path, check_06: bool, check_07: bool):
    """risk_id 集合四文件比对：矩阵 vs 正文（AC2 已查，此处汇总）vs 落实表 vs 台账。
    台账方向：多出 → FAIL；缺失 → WARN（台账仅登记义务型风险属常见合法情形）。"""
    if not matrix_ids:
        return
    body_ids = set()
    for _, text in report:
        body_ids |= extract_risk_ids(text)

    txn_ids = set()
    if check_06:
        for p in sorted(txn_dir.glob("*落实表*.md")) if txn_dir.is_dir() else []:
            text, _ = read_text(p)
            if text:
                txn_ids |= extract_risk_ids(text)

    ledger_ids, ledger_src = set(), ""
    if check_07 and post_dir.is_dir():
        ljson = post_dir / "ledger.json"
        if ljson.exists():
            data, err = load_json(ljson)
            if err:
                rep.warn_skip("ledger.json", err)
            else:
                ledger_ids |= _ledger_json_ids(data)
                ledger_src = "ledger.json"
        for p in sorted(post_dir.glob("*台账*.md")):
            text, _ = read_text(p)
            if text:
                ledger_ids |= extract_risk_ids(text)
                ledger_src = ledger_src or p.name
        if not ledger_ids:
            rep.warn_skip("AC4 台账比对", "07_post_invest 无 ledger.json / *台账*.md")

    for n in sorted(txn_ids - matrix_ids):
        rep.emit("FAIL", "AC4", f"{fmt_rid(n)} 出现在落实表但 risk_matrix 不存在")
    for n in sorted(ledger_ids - matrix_ids):
        rep.emit("FAIL", "AC4", f"{fmt_rid(n)} 出现在台账（{ledger_src}）但 risk_matrix 不存在")
    for n in sorted(matrix_ids - ledger_ids) if (check_07 and ledger_ids) else []:
        rep.emit("WARN", "AC4", f"{fmt_rid(n)} 未进入台账（可能仅义务型风险入账，人工判读）")

    parts = [f"矩阵 {len(matrix_ids)}", f"正文 {len(matrix_ids & body_ids)}"]
    if check_06:
        parts.append(f"落实表 {len(matrix_ids & txn_ids)}")
    if check_07 and ledger_ids:
        parts.append(f"台账 {len(matrix_ids & ledger_ids)}")
    ok = not (txn_ids - matrix_ids) and not (ledger_ids - matrix_ids)
    if ok:
        rep.emit("PASS", "AC4", f"risk_id 一致性检查通过 ({len(matrix_ids)}/{len(matrix_ids)})",
                 ["，".join(parts)])


def _clean_cell(text: str) -> str:
    """表格单元格提取后截去行内标注（（…）/[…]/emoji 标签），只留主体值"""
    cut = re.search(r"[（(\[{✅📌⚠️❌]", text)
    return (text[:cut.start()] if cut else text).strip()


def _dossier_company(dossier: str) -> tuple[str | None, str | None]:
    """从 Dossier §1 提取公司全称与简称（剥离行内标注）"""
    full = re.search(r"公司全称\s*\|\s*([^|\n]+)", dossier)
    short = re.search(r"项目简称\s*\|\s*([^|\n]+)", dossier)
    f = _clean_cell(full.group(1)) if full else None
    s = _clean_cell(short.group(1)) if short else None
    return f or None, s or None


def check_ac4_company(rep: Reporter, dossier: str | None, matrix: dict | None,
                      report: list[tuple[str, str]], txn_dir: Path, post_dir: Path,
                      check_06: bool, check_07: bool):
    """公司名一致性：Dossier §1 全称 vs 各产出（WARN 级——简称/曾用名属常见合法用法）"""
    if not dossier:
        rep.warn_skip("AC4 公司名一致性", "project_dossier.md 未找到")
        return
    full, short = _dossier_company(dossier)
    if not full:
        rep.warn_skip("AC4 公司名一致性", "Dossier §1 未找到「公司全称」字段")
        return

    artifacts: list[tuple[str, str]] = []
    matrix_project = matrix.get("project") or matrix.get("project_name") if isinstance(matrix, dict) else None
    if isinstance(matrix_project, str) and matrix_project:
        artifacts.append(("risk_matrix.json.project", matrix_project))
    for name, text in report:
        artifacts.append((f"报告正文（{name}）", text))
        break  # 只查最新主报告
    if check_06 and txn_dir.is_dir():
        for p in sorted(txn_dir.glob("*.md"))[:6]:
            text, _ = read_text(p)
            if text:
                artifacts.append((f"06_txn_docs/{p.name}", text))
    if check_07 and post_dir.is_dir():
        lj = post_dir / "ledger.json"
        if lj.exists():
            data, _ = load_json(lj)
            if isinstance(data, dict) and isinstance(data.get("project"), str):
                artifacts.append(("ledger.json.project", data["project"]))

    absent = [label for label, text in artifacts if full not in text]
    if absent:
        hint = f"（可能使用简称「{short}」或曾用名，人工判读）" if short else "（可能使用简称或曾用名，人工判读）"
        rep.emit("WARN", "AC4", f"公司全称「{full}」未出现在：{', '.join(absent)} {hint}")
    else:
        rep.emit("PASS", "AC4", f"公司名一致性通过（全称「{full}」见全部 {len(artifacts)} 处产出）")


def _parse_date(s: str):
    m = DATE_VALUE_RE.search(s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        from datetime import date
        return date(y, mo, d)
    except ValueError:
        return None


def check_ac4_dates(rep: Reporter, project_dir: Path, matrix: dict | None,
                    report: list[tuple[str, str]], scope: list[str]):
    """日期一致性：matrix.generated_date / 各 output.json.date / 报告出具日期 跨度告警"""
    found: list[tuple[str, object]] = []
    if matrix and isinstance(matrix.get("generated_date"), str):
        d = _parse_date(matrix["generated_date"])
        if d:
            found.append(("risk_matrix.generated_date", d))
    for name, text in report[:1]:
        m = re.search(r"出具日期[^\d]{0,6}(\d{4}\s*[年./-]\s*\d{1,2}\s*[月./-]\s*\d{1,2})", text)
        if m:
            d = _parse_date(m.group(1))
            if d:
                found.append((f"报告出具日期（{name}）", d))
        break
    for phase in scope:
        opath = project_dir / phase / "output.json"
        if opath.exists():
            data, _ = load_json(opath)
            if isinstance(data, dict) and isinstance(data.get("date"), str):
                d = _parse_date(data["date"])
                if d:
                    found.append((f"{phase}/output.json.date", d))
    if len(found) < 2:
        rep.warn_skip("AC4 日期一致性", "可解析的产出日期不足 2 处")
        return
    ds = [d for _, d in found]
    span = (max(ds) - min(ds)).days
    if span > DATE_SPAN_WARN_DAYS:
        rep.emit("WARN", "AC4", f"产出日期跨度 {span} 天（> {DATE_SPAN_WARN_DAYS}），请确认版本基线一致",
                 [f"{label}: {d.isoformat()}" for label, d in found])
    else:
        rep.emit("PASS", "AC4", f"日期一致性通过（跨度 {span} 天，{len(found)} 处）")


# ── AC5 降级显式化 ────────────────────────────────────────────────────

def check_ac5(rep: Reporter, project_dir: Path, scope: list[str]):
    """全文搜索绝对性表述，附近无来源标注/降级声明 → WARN（人工判读）"""
    targets: list[tuple[str, str]] = []
    dossier, _ = read_text(project_dir / "project_dossier.md")
    if dossier:
        targets.append(("project_dossier.md", dossier))
    for phase in ("04_risk_report", "05_report_review", "06_txn_docs", "07_post_invest"):
        if phase not in scope:
            continue
        pdir = project_dir / phase
        if not pdir.is_dir():
            continue
        for p in sorted(pdir.glob("*.md")):  # 只扫顶层产出，不进 work/底稿
            text, _ = read_text(p)
            if text is not None:
                targets.append((f"{phase}/{p.name}", text))
    if not targets:
        rep.warn_skip("AC5 降级检查", "范围内无产出 md")
        return

    hits = []
    for name, text in targets:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            phrase = next((p for p in ABSOLUTE_PHRASES if p in line), None)
            if not phrase:
                continue
            window = "\n".join(lines[max(0, i - 1):i + 2])
            if not DEGRADE_MARKER_RE.search(window):
                pos = line.find(phrase)
                hits.append(f"{name}:L{i + 1} \"{snippet(line, pos)}\"")
    if hits:
        rep.emit("WARN", "AC5", f"{len(hits)} 处绝对性表述附近无来源标注/降级声明（人工判读）", hits)
    else:
        rep.emit("PASS", "AC5", f"绝对性表述降级检查通过（扫描 {len(targets)} 个文件）")


# ── 主流程 ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="风控交付验收脚本：Mechanical preflight validator for CONTRACT acceptance checks")
    parser.add_argument("project_dir", help="项目目录路径（如 projects/某项目）")
    parser.add_argument("--phase", choices=PHASES, default=None,
                        help="限定检查的 Phase 目录（默认检查全部）")
    parser.add_argument("--sample", type=int, default=20,
                        help="AC3 抽样展示上限（默认 20）")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出 PASS 项细节")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"错误：项目目录不存在 - {project_dir}", file=sys.stderr)
        sys.exit(2)

    scope = [args.phase] if args.phase else PHASES
    check_04 = "04_risk_report" in scope
    check_06 = "06_txn_docs" in scope
    check_07 = "07_post_invest" in scope

    rep = Reporter(args.verbose)
    print(f"项目目录：{project_dir}")
    print(f"检查范围：{args.phase or '全部 Phase'}")
    print("-" * 60)

    if not any((project_dir / p).is_dir() for p in PHASES):
        rep.warn_skip("全部检查", "未发现任何 Phase 产出目录（01~07）")

    # ── 加载核心锚点 ──
    matrix_path = project_dir / "04_risk_report" / "risk_matrix.json"
    matrix = None
    if matrix_path.exists():
        matrix, err = load_json(matrix_path)
        if err or not isinstance(matrix, dict):
            rep.emit("FAIL", "Schema", f"risk_matrix.json 无法解析（{err}）")
            matrix = None
    elif check_04:
        rep.warn_skip("risk_matrix.json", "04_risk_report 下未找到（AC2/AC4 依赖）")

    matrix_ids: set[int] = set()
    if isinstance(matrix, dict) and isinstance(matrix.get("risks"), list):
        for r in matrix["risks"]:
            if isinstance(r, dict):
                rid = r.get("risk_id", r.get("id"))
                m = re.fullmatch(r"R(\d{2,3})", str(rid)) if rid else None
                if m:
                    matrix_ids.add(int(m.group(1)))

    report: list[tuple[str, str]] = []
    if check_04:
        report = find_report(project_dir / "04_risk_report")
        if not report:
            rep.warn_skip("AC2/AC3 报告正文", "04_risk_report 下未找到 report_ch*.md 或 *风控报告*.md（排除投委会版）")

    txn_dir = project_dir / "06_txn_docs"
    post_dir = project_dir / "07_post_invest"
    dossier, _ = read_text(project_dir / "project_dossier.md")

    # ── Schema ──
    check_output_json(rep, project_dir, scope)
    matrix_ok = check_risk_matrix_schema(rep, matrix, matrix_path) if matrix else False
    check_certainty_labels(rep, project_dir, scope)

    # ── 必须产物（CONTRACT §6：completed 缺产物 = FAIL）──
    check_required_artifacts(rep, project_dir, scope)

    # ── AC2 ──
    if check_04:
        if matrix_ids and report:
            check_ac2_report(rep, matrix_ids, report)
        if report:
            check_ac3(rep, report, args.sample)
    if check_06:
        if matrix_ids:
            check_ac2_txn(rep, matrix_ids, txn_dir)
        else:
            rep.warn_skip("AC2 交易文件覆盖度", "risk_matrix 不可用")

    # ── AC4 ──
    if check_04 and matrix_ids:
        check_ac4_risk_ids(rep, matrix_ids, report, txn_dir, post_dir, check_06, check_07)
        check_ac4_company(rep, dossier, matrix, report, txn_dir, post_dir, check_06, check_07)
        check_ac4_dates(rep, project_dir, matrix, report, scope)
    # AC4 金额一致性不做脆弱 regex 机械比对：逐 Phase 声明人工核验义务（不计数、不影响退出码）
    for phase in scope:
        if phase in AC4_AMOUNT_PHASES:
            rep.manual("AC4-amounts", f"金额一致性需人工核验（{phase}）")

    # ── AC5 ──
    check_ac5(rep, project_dir, scope)

    # ── 汇总 ──
    print("-" * 60)
    c = rep.counts
    print(f"验收结果：PASS {c['PASS']} | WARN {c['WARN']} | FAIL {c['FAIL']}"
          f"（WARN 为人工判读项，不计入失败）")
    sys.exit(0 if c["FAIL"] == 0 else 1)


if __name__ == "__main__":
    main()
