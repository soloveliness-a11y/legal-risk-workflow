"""静态检查：编译、bash 语法、JSON/YAML 合法性、Skill 规范、Markdown 内链。"""
import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path

import yaml

SKIP_TEXT_DIRS = {".git", "__pycache__", "node_modules"}


def test_compileall_scripts(repo_root):
    r = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "scripts"],
        cwd=repo_root, capture_output=True,
    )
    assert r.returncode == 0, r.stderr.decode()


def test_bash_syntax_first_run(repo_root):
    r = subprocess.run(["bash", "-n", "scripts/first_run.sh"], cwd=repo_root, capture_output=True)
    assert r.returncode == 0, r.stderr.decode()


def test_all_json_files_parse(repo_root):
    files = [f for f in repo_root.rglob("*.json") if not any(p in SKIP_TEXT_DIRS for p in f.parts)]
    assert files, "应至少有 json 文件"
    for f in files:
        json.loads(f.read_text(encoding="utf-8"))


def test_config_example_parses(repo_root):
    data = yaml.safe_load((repo_root / "config.example.yaml").read_text(encoding="utf-8"))
    for key in ("paddleocr", "qcc", "ima", "security", "paths"):
        assert key in data, f"config.example.yaml 缺节 {key}"


def test_skills_spec_12_of_12(repo_root):
    r = subprocess.run(
        [sys.executable, "scripts/tools/validate_skills.py"],
        cwd=repo_root, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "12 通过 / 0 失败" in r.stdout


def test_skill_frontmatter_aliases(repo_root):
    """重命名的技能描述应保留旧下划线名作为检索别名。"""
    renames = {
        "dd-check": "dd_check", "dd-interview": "dd_interview", "dd-prep": "dd_prep",
        "industry-research": "industry_research", "legal-research": "legal_research",
        "post-invest-check": "post_invest_check", "qcc-scan": "qcc_scan",
        "report-review": "report_review", "risk-report": "risk_report", "txn-docs": "txn_docs",
    }
    for new, old in renames.items():
        text = (repo_root / "skills" / new / "SKILL.md").read_text(encoding="utf-8")
        assert old in text.split("---")[1], f"{new} 描述缺少旧称别名 {old}"


def test_md_internal_links(repo_root):
    bad = []
    for f in repo_root.rglob("*.md"):
        if any(p in SKIP_TEXT_DIRS for p in f.parts):
            continue
        text = f.read_text(encoding="utf-8")
        cleaned = re.sub(r"`[^`]*`", "", text)  # 跳过行内代码（正则模式等伪链接）
        for m in re.finditer(r"\[[^\]]*\]\(([^)#\s]+)[^)]*\)", cleaned):
            link = m.group(1)
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            if not (f.parent / link).resolve().exists():
                bad.append(f"{f}: {link}")
    assert not bad, f"内部链接损坏: {bad}"


def test_no_broken_example_py(repo_root):
    """reference 下不应再有带占位符的 .py（compileall 必须全绿）。"""
    ref = repo_root / "scripts" / "reference"
    if ref.is_dir():
        assert not list(ref.glob("*.py")), "scripts/reference 只允许 Markdown 存档"
