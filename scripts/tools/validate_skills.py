#!/usr/bin/env python3
"""
Skill 规范校验器（Agent Skills specification）

依据 https://agentskills.io/specification 校验 skills/ 下每个技能：
  1. SKILL.md 存在且含 YAML frontmatter
  2. name：必填，1-64 字符，仅小写字母/数字/连字符，不得以连字符开头结尾或连续
  3. name 必须与父目录名一致
  4. description：必填，1-1024 字符
  5. compatibility（可选）：≤500 字符
  6. metadata（可选）：所有值必须是字符串（版本、tags 等不得用数字/数组）
  7. 顶层字段仅允许 name/description/license/compatibility/metadata/allowed-tools

用法：
  python3 scripts/tools/validate_skills.py [skills_dir]
退出码：0=全部通过 1=存在 FAIL
"""

import re
import sys
from pathlib import Path

try:
    import yaml
    _YAML = True
except ImportError:
    _YAML = False

ALLOWED_TOP_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def parse_frontmatter(text: str):
    """返回 (frontmatter_dict, 错误列表)。无 pyyaml 时用极简解析（足够本工具）。"""
    errors = []
    m = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", text, re.S)
    if not m:
        return None, ["缺少 YAML frontmatter（--- ... ---）"]
    raw = m.group(1)
    if _YAML:
        try:
            data = yaml.safe_load(raw) or {}
        except yaml.YAMLError as e:
            return None, [f"frontmatter YAML 解析失败: {e}"]
        return data, errors
    # 简易解析：仅支持 key: value 与一级 metadata 嵌套
    data, current_meta = {}, None
    for line in raw.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith("  ") and current_meta:
            k, _, v = line.strip().partition(":")
            v = v.strip().strip('"').strip("'")
            data[current_meta][k] = v
        elif not line.startswith((" ", "\t")):
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if v == "":
                if k == "metadata":
                    data[k] = {}
                    current_meta = k
                else:
                    data[k] = {}
                    current_meta = k
            else:
                if v.startswith("|") or v.startswith(">"):
                    data[k] = "<block>"
                else:
                    data[k] = v.strip('"').strip("'")
                current_meta = None
    return data, errors


def validate_skill(skill_dir: Path) -> list:
    errors = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"缺少 SKILL.md"]

    text = skill_md.read_text(encoding="utf-8")
    data, fm_errors = parse_frontmatter(text)
    errors.extend(fm_errors)
    if data is None:
        return errors

    # name
    name = data.get("name")
    if not name or not isinstance(name, str):
        errors.append("name 缺失或非字符串")
    else:
        if not (1 <= len(name) <= 64):
            errors.append(f"name 长度 {len(name)} 超出 1-64")
        if not NAME_RE.match(name):
            errors.append(f"name '{name}' 不符合规范（仅小写字母/数字/连字符，不得首尾或连续连字符）")
        if name != skill_dir.name:
            errors.append(f"name '{name}' 与目录名 '{skill_dir.name}' 不一致")

    # description
    desc = data.get("description")
    if not desc or not isinstance(desc, str) or not desc.strip():
        errors.append("description 缺失或为空")
    elif desc == "<block>":
        pass  # 简易解析无法取多行长度，跳过长度检查
    elif len(desc) > 1024:
        errors.append(f"description 长度 {len(desc)} 超出 1024")

    # compatibility
    compat = data.get("compatibility")
    if compat is not None and isinstance(compat, str) and len(compat) > 500:
        errors.append(f"compatibility 长度 {len(compat)} 超出 500")

    # metadata 值必须是字符串
    meta = data.get("metadata")
    if meta is not None:
        if not isinstance(meta, dict):
            errors.append("metadata 必须是映射（string -> string）")
        else:
            for k, v in meta.items():
                if not isinstance(v, str):
                    errors.append(f"metadata.{k} 的值必须是字符串（当前 {type(v).__name__}: {v!r}）")

    # 顶层未知字段
    for k in data:
        if k not in ALLOWED_TOP_KEYS:
            errors.append(f"顶层字段 '{k}' 不在规范允许列表（version 等应放入 metadata）")

    return errors


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skill 规范校验器（Agent Skills specification）")
    parser.add_argument("skills_dir", nargs="?", default=None,
                        help="技能目录（默认：仓库 skills/）")
    args = parser.parse_args()

    if args.skills_dir:
        root = Path(args.skills_dir)
    else:
        root = Path(__file__).resolve().parent.parent.parent / "skills"
    if not root.is_dir():
        print(f"❌ 目录不存在: {root}", file=sys.stderr)
        sys.exit(2)

    skill_dirs = sorted(d for d in root.iterdir() if d.is_dir())

    passed, failed = 0, 0
    for d in skill_dirs:
        errors = validate_skill(d)
        if errors:
            failed += 1
            print(f"❌ {d.name}")
            for e in errors:
                print(f"     - {e}")
        else:
            passed += 1
            print(f"✅ {d.name}")

    print(f"\n校验结果: {passed} 通过 / {failed} 失败（共 {passed + failed}）")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
