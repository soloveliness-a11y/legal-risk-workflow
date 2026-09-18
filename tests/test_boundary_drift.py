"""外传分级一致性：CONTRACT §7.2 与 SECURITY_PRIVACY.md 不得漂移。

S1 敏感类别必须同时出现在两份文件中，且任何"可外传/可上传"语境附近
不得出现 S1 类别词。背景：v0.2.0 曾出现 SECURITY_PRIVACY 把访谈纪要列为
S1、CONTRACT 却把访谈转写稿列为可上传外部 OCR 的直接冲突（v0.2.1 修复）。
"""
import re

from pathlib import Path

S1_TOKENS = ["合同", "员工花名册", "财务报表", "尽调报告", "投资建议书", "访谈"]
ALLOW_CONTEXT_RE = re.compile(r"(可上传外部|可经外部 OCR|确认后可上传|可外传)")


def _files(repo_root):
    return [
        repo_root / "skills" / "risk-workflow" / "CONTRACT.md",
        repo_root / "SECURITY_PRIVACY.md",
    ]


def test_s1_categories_defined_in_both(repo_root):
    for f in _files(repo_root):
        text = f.read_text(encoding="utf-8")
        missing = [t for t in S1_TOKENS if t not in text]
        assert not missing, f"{f.name} 缺 S1 类别词 {missing}（外传分级漂移）"


# 信任路径豁免词：放行语境必须伴随这些前提之一，否则视为漂移
TRUST_EXEMPT = ["trusted-provider", "信任", "保密义务", "保密与不训练"]


def test_no_s1_in_allow_context(repo_root):
    for f in _files(repo_root):
        text = f.read_text(encoding="utf-8")
        for m in ALLOW_CONTEXT_RE.finditer(text):
            ctx = text[max(0, m.start() - 120):m.end() + 120]
            if any(w in ctx for w in TRUST_EXEMPT):
                continue  # 信任路径（已核验服务商保密/不训练承诺）下的有条件放行
            hit = [t for t in S1_TOKENS if t in ctx]
            assert not hit, f"{f.name} 在'可外传'语境附近出现 S1 类别 {hit}：…{ctx}…"


def test_trust_path_requires_confidentiality_clauses(repo_root):
    """声明 trusted-provider 的文件必须同时写明保密义务与不用于训练两个前提。"""
    for f in _files(repo_root):
        text = f.read_text(encoding="utf-8")
        if "trusted-provider" in text:
            assert "保密义务" in text or "保密与不训练" in text, f"{f.name} 信任路径缺保密前提"
            assert "不用于" in text, f"{f.name} 信任路径缺'不用于模型训练'前提"
