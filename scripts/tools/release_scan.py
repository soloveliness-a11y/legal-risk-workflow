#!/usr/bin/env python3
"""
发布前匿名化与凭据扫描器

用途：提交/发布前扫描仓库文本，检查：
  1. 内置模式：手机号、邮箱、身份证号（含校验位验证）、常见 API 密钥/令牌形态
  2. 外部词表：维护者私有词（公司名、项目名、内部域名等），支持明文或 sha256 摘要行

外部词表不进仓库（私有词禁止以明文 denylist 形式提交）：
  - 路径来源：--wordlist FILE 或 config.yaml 的 security.wordlist（逗号分隔多路径）
  - 词表格式：每行一个词；明文行直接匹配；`sha256:<hex>` 行按摘要匹配
    （短词的裸 sha256 可被穷举还原，仅建议对较长短语使用；短词请用本地明文词表）
  - 词表文件建议放在仓库外（如 ~/.config/legal-risk-workflow/scan_words.txt）

能力边界（重要）：
  - 默认只扫描工作树（跳过 .git 目录）
  - --history 额外扫描 git 历史：所有可达 blob（文件历史快照）、commit message、tag message
  - 不覆盖 GitHub Release 文案、Issue、PR、Wiki 等仅存在于远端的面——发布前须人工复核
  - --history 只证明本地仓库历史干净；已推送后又在远端丢弃/改写的对象不在本地，无法覆盖

退出码：0=未发现 1=有发现 2=参数错误

用法：
  python3 release_scan.py                      # 扫描工作树（内置模式 + 已配置词表）
  python3 release_scan.py --history            # 同时扫描 git 历史（文件快照 + 提交/标签信息）
  python3 release_scan.py --wordlist ~/private/scan_words.txt
  python3 release_scan.py --show               # 显示完整命中内容（默认脱敏显示）
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys

_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from config_loader import get_config

# ── 内置模式（不含任何私有词）──────────────────────────────────────────

BUILTIN_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("邮箱", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("身份证号形态", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")),
    ("API令牌-AKIA", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("API令牌-ghp", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("API令牌-sk", re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")),
    ("API令牌-xox", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Bearer凭据", re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}")),
    ("私钥块", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

ID_CARD_WEIGHTS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
ID_CARD_CHECK = "10X98765432"

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}
TEXT_EXTS = {
    ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".html",
    ".css", ".js", ".ts", ".sh", ".example", ".gitignore", ".cfg", ".ini",
    ".noext",
}
TEXT_FILENAMES = {".gitignore", ".dockerignore", "LICENSE", "NOTICE.md"}


def valid_id_card(num: str) -> bool:
    """18 位身份证校验位验证，减少误报。"""
    try:
        total = sum(int(num[i]) * ID_CARD_WEIGHTS[i] for i in range(17))
        return ID_CARD_CHECK[total % 11] == num[17].upper()
    except (ValueError, IndexError):
        return False


def load_wordlist(paths: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """读取词表，返回（明文词列表, (词表路径, sha256摘要) 列表）。"""
    plain: list[str] = []
    digests: list[tuple[str, str]] = []
    for p in paths:
        p = os.path.expanduser(p.strip())
        if not p or not os.path.isfile(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.lower().startswith("sha256:"):
                    digests.append((p, line[7:].strip().lower()))
                else:
                    plain.append(line)
    return plain, digests


def is_text_path(name: str) -> bool:
    ext = os.path.splitext(name)[1].lower()
    return name in TEXT_FILENAMES or ext in TEXT_EXTS or not ext


def iter_text_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if is_text_path(name):
                yield os.path.join(dirpath, name)


def mask(text: str) -> str:
    if len(text) <= 4:
        return text[0] + "***"
    return text[:2] + "***" + text[-2:]


def line_hits(line: str, plain_words: list[str], digests: list[tuple[str, str]],
              show: bool) -> list[str]:
    """对单行文本执行全部检测，返回命中描述列表。"""
    hits: list[str] = []
    for label, pattern in BUILTIN_PATTERNS:
        for m in pattern.finditer(line):
            text = m.group(0)
            if label == "身份证号形态" and not valid_id_card(text):
                continue
            hits.append(f"{label}:{text if show else mask(text)}")
    for word in plain_words:
        if word and word in line:
            hits.append(f"私有词:{word if show else mask(word)}")
    if digests:
        for token in re.split(r"[^\w\u4e00-\u9fff]+", line):
            if not token:
                continue
            for src, digest in digests:
                if hashlib.sha256(token.encode("utf-8")).hexdigest() == digest:
                    hits.append(f"私有词(摘要@{os.path.basename(src)}):{token if show else mask(token)}")
    return hits


def scan(root: str, plain_words: list[str], digests: list[tuple[str, str]], show: bool):
    """扫描工作树文本文件。"""
    findings: list[str] = []
    for filepath in iter_text_files(root):
        rel = os.path.relpath(filepath, root)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    hits = line_hits(line, plain_words, digests, show)
                    if hits:
                        findings.append(f"{rel}:{lineno}  {'  '.join(sorted(set(hits)))}")
        except OSError:
            continue
    return findings


def _git(root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", root, *args], capture_output=True)


def scan_history(root: str, plain_words: list[str], digests: list[tuple[str, str]], show: bool):
    """扫描 git 历史中所有可达对象：文件快照 blob + commit message + tag message。"""
    probe = _git(root, "rev-parse", "--git-dir")
    if probe.returncode != 0:
        print("❌ --history 需要在 git 仓库内运行（未检测到 .git）", file=sys.stderr)
        sys.exit(2)

    findings: list[str] = []

    # 1) 所有可达 blob（文件历史快照），按 sha 去重
    proc = _git(root, "rev-list", "--objects", "--all")
    if proc.returncode != 0:
        print(f"❌ git rev-list 失败：{proc.stderr.decode('utf-8', 'ignore').strip()}", file=sys.stderr)
        sys.exit(2)
    blob_paths: dict[str, str] = {}
    for raw in proc.stdout.decode("utf-8", "ignore").splitlines():
        parts = raw.split(" ", 1)
        if len(parts) != 2:
            continue
        sha, path = parts
        if is_text_path(os.path.basename(path)):
            blob_paths.setdefault(sha, path)
    for sha, path in blob_paths.items():
        blob = _git(root, "cat-file", "blob", sha)
        if blob.returncode != 0 or b"\x00" in blob.stdout:
            continue
        text = blob.stdout.decode("utf-8", "ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            hits = line_hits(line, plain_words, digests, show)
            if hits:
                findings.append(f"history:{sha[:12]}:{path}:{lineno}  {'  '.join(sorted(set(hits)))}")

    # 2) commit message
    proc = _git(root, "log", "--all", "--format=%H%x1f%B%x1e")
    for record in proc.stdout.decode("utf-8", "ignore").split("\x1e"):
        if "\x1f" not in record:
            continue
        sha, body = record.split("\x1f", 1)
        for lineno, line in enumerate(body.splitlines(), 1):
            hits = line_hits(line, plain_words, digests, show)
            if hits:
                findings.append(f"commit-message:{sha[:12]}:{lineno}  {'  '.join(sorted(set(hits)))}")

    # 3) tag message（附注标签）
    proc = _git(root, "for-each-ref", "--format=%(refname)%00%(contents)")
    for record in proc.stdout.decode("utf-8", "ignore").split("\n"):
        if "\x00" not in record:
            continue
        ref, body = record.split("\x00", 1)
        for lineno, line in enumerate(body.splitlines(), 1):
            hits = line_hits(line, plain_words, digests, show)
            if hits:
                findings.append(f"tag-message:{ref}:{lineno}  {'  '.join(sorted(set(hits)))}")

    return findings


def main():
    parser = argparse.ArgumentParser(
        description="发布前匿名化与凭据扫描器（默认只扫工作树，--history 加扫 git 历史；"
                    "GitHub Release/Issue/PR 等远端面不在扫描范围，发布前人工复核）")
    parser.add_argument("--root", default=None, help="仓库根目录（默认：脚本所在仓库根）")
    parser.add_argument("--wordlist", action="append", default=None,
                        help="私有词表路径（可重复；或经 config.yaml security.wordlist 配置）")
    parser.add_argument("--history", action="store_true",
                        help="同时扫描 git 历史：全部可达文件快照 + commit message + tag message")
    parser.add_argument("--show", action="store_true", help="显示完整命中内容（默认脱敏）")
    args = parser.parse_args()

    root = args.root or os.path.dirname(_SCRIPT_DIR)
    root = os.path.abspath(os.path.expanduser(root))

    wordlist_paths = list(args.wordlist or [])
    cfg_val = get_config().get("security.wordlist", "")
    if isinstance(cfg_val, str) and cfg_val.strip():
        wordlist_paths.extend(cfg_val.split(","))

    plain_words, digests = load_wordlist(wordlist_paths)
    if wordlist_paths and not plain_words and not digests:
        print("⚠️ 已指定词表路径但未加载到任何词条，请检查词表文件", file=sys.stderr)

    print(f"🔍 扫描根目录: {root}")
    print(f"   内置模式 {len(BUILTIN_PATTERNS)} 类；私有词 {len(plain_words)} 条 + 摘要 {len(digests)} 条")

    findings = scan(root, plain_words, digests, args.show)
    if args.history:
        print("   含 git 历史扫描（文件快照 + commit/tag message）")
        findings += scan_history(root, plain_words, digests, args.show)

    if findings:
        print(f"\n❌ 发现 {len(findings)} 处命中：\n")
        for f in findings:
            print(f"  {f}")
        print("\n处置：真实凭据立即作废并从来源移除；私有词改写为通用表述后再提交。"
              "命中于 history:/commit-message:/tag-message: 前缀的，说明 git 历史不干净，"
              "按 ROADMAP 发布安全铁律处理（不能以普通 commit 修补）。")
        sys.exit(1)
    print("\n✅ 未发现命中（内置模式 + 已配置词表）")
    sys.exit(0)


if __name__ == "__main__":
    main()
