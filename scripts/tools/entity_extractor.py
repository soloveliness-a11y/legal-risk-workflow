#!/usr/bin/env python3
"""
NER 实体提取器 V1.0
⚠️ 状态：未接入任何Skill，预留能力。
基于正则规则+关键词匹配，从风控报告/尽调文档中提取实体。
提取类型：公司名称、关键人员、关联方、地址、日期、金额、法律法规

用法:
  python3 entity_extractor.py --input report.md --output entities.json
  python3 entity_extractor.py --input report.md --format markdown
  python3 entity_extractor.py --input report.md --types company,person,date
  python3 entity_extractor.py --input report.md --dedup-threshold 0.8
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# ── 实体提取规则 ──────────────────────────────────────────────

ENTITY_RULES = {
    # 公司名称：中文全称 + 简称
    "company": {
        "patterns": [
            # 完整公司名称（含"公司/企业/合伙"结尾，需有行业词）
            r'([\u4e00-\u9fff]+(?:股份有限|有限责任|有限合伙)[\u4e00-\u9fff]*?(?:公司|企业))',
            # 常见结尾的公司名（需4字以上且含行业关键词）
            r'([\u4e00-\u9fff]{2,}(?:科技|技术|投资|咨询|管理|发展|控股|资本|基金|资产|网络|信息|数据|智能|机器人|装备|医疗|健康|生物|医药|新材料|新能源|航天|航空|半导体|芯片|软件|通信|电子|光电|光学|储能|碳|材料)[\u4e00-\u9fff]*?(?:有限公司|股份公司|集团公司|合伙企业|中心|院|所))',
            # 括号内的公司简称（限"以下简称"语境，3-15字纯中文）
            r'以下简称[""「」]([^""「」]{2,15})[""「」]',
            # 英文公司名
            r'([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*\s+(?:Inc\.|Corp\.|Ltd\.|LLC|Group|Holdings|Co\.|Company))',
        ],
        "blacklist": [
            "以下简称", "以下简称\"", "以下称", "以下简称为",
            "目标公司", "标的公司", "投资标的",
            "公司", "本公司", "母公司", "子公司", "分公司",
        ]
    },
    
    # 人名
    "person": {
        "patterns": [
            # 姓名后跟身份/职务
            r'([\u4e00-\u9fff]{2,4})\s*(?:先生|女士|总|教授|博士|律师)',
            # 身份标识词后跟姓名
            r'(?:创始人|实控人|法定代表人|董事长|总经理|CEO|CTO|COO|CFO|董事|监事|合伙人)\s*[:：]?\s*([\u4e00-\u9fff]{2,4})(?:\s|，|。|、|；|,|\.|（|\(|$)',
            # "持有/持股/控制"语境中的姓名
            r'(?:股东|持有|持股|控制|代持|转让)\s*([\u4e00-\u9fff]{2,3})(?:\s|，|。|、|；|持股|持有|的|等|共)',
        ],
        "blacklist": [
            "公司", "企业", "项目", "报告", "文件", "股东", "投资", "基金",
            "管理", "技术", "发展", "有限", "股份", "合伙", "控股", "集团",
            "本人", "三方", "双方", "各方", "甲方", "乙方", "丙方", "丁方",
            "风险", "财务", "业务", "产品", "市场", "行业", "客户",
            "决议", "大会", "会议", "责任", "权利", "义务",
        ]
    },
    
    # 日期
    "date": {
        "patterns": [
            # YYYY年MM月DD日
            r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
            # YYYY年MM月
            r'(\d{4})\s*年\s*(\d{1,2})\s*月(?!\s*\d)',
            # YYYY.MM.DD / YYYY-MM-DD / YYYY/MM/DD
            r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})',
            # YYYY.MM / YYYY-MM
            r'(\d{4})[.\-/](\d{1,2})(?![.\-/]\d)',
        ],
        "blacklist": []
    },
    
    # 金额
    "amount": {
        "patterns": [
            # 中文金额
            r'([\d,.]+)\s*(?:万元|亿元|万元人民币|亿元人民币|美元|港币|万|亿)',
            # 带符号金额
            r'[¥￥$]\s*([\d,.]+)\s*(?:万|亿)?',
            # 百分比
            r'([\d.]+)\s*%',
        ],
        "blacklist": []
    },
    
    # 法律法规
    "regulation": {
        "patterns": [
            r'《([^》]{2,80}?)》',
        ],
        "blacklist": [
            "以下简称", "投资协议", "股东协议", "公司章程",
        ]
    },
    
    # 地址
    "address": {
        "patterns": [
            # 中国地址
            r'((?:中国)?(?:北京|上海|天津|重庆|广东|浙江|江苏|四川|湖北|湖南|山东|福建|安徽|河南|河北|陕西|辽宁|吉林|黑龙江|江西|山西|甘肃|青海|贵州|云南|海南|台湾|香港|澳门|内蒙古|广西|西藏|宁夏|新疆)(?:省|市|自治区|特别行政区)?[^，。；\n]{5,50}?(?:路|街|道|号|区|园|大厦|中心|广场|楼|层|室|栋|座))',
        ],
        "blacklist": []
    },
}


def extract_entities(text, entity_types=None, dedup_threshold=0.8):
    """从文本中提取实体"""
    if entity_types is None:
        entity_types = list(ENTITY_RULES.keys())
    
    results = defaultdict(list)
    
    for etype in entity_types:
        if etype not in ENTITY_RULES:
            continue
        
        rule = ENTITY_RULES[etype]
        blacklist = rule.get("blacklist", [])
        
        for pattern in rule["patterns"]:
            matches = re.finditer(pattern, text)
            for match in matches:
                # 提取匹配内容
                if etype == "date":
                    groups = [g for g in match.groups() if g]
                    value = "-".join(groups)
                    raw = match.group(0)
                elif etype == "amount":
                    value = match.group(0)
                    raw = match.group(0)
                else:
                    value = match.group(1) if match.lastindex else match.group(0)
                    raw = match.group(0)
                
                if not value or len(value.strip()) < 2:
                    continue
                
                # 黑名单过滤
                if any(bl in value for bl in blacklist):
                    continue
                
                # 日期子串去重：如已有"2025-11-18"则跳过"2025-11"
                if etype == "date":
                    is_sub = False
                    for existing in results[etype]:
                        if existing["value"].startswith(value) and len(existing["value"]) > len(value):
                            is_sub = True
                            break
                    if is_sub:
                        continue
                
                # 去重（模糊匹配）
                is_dup = False
                for existing in results[etype]:
                    if _similarity(value, existing["value"]) >= dedup_threshold:
                        is_dup = True
                        break
                
                if not is_dup:
                    results[etype].append({
                        "value": value.strip(),
                        "raw": raw.strip(),
                        "position": match.start(),
                    })
    
    return dict(results)


def _similarity(a, b):
    """简单的字符串相似度"""
    if a == b:
        return 1.0
    if len(a) == 0 or len(b) == 0:
        return 0.0
    
    # 包含关系
    if a in b or b in a:
        shorter = min(len(a), len(b))
        longer = max(len(a), len(b))
        return shorter / longer
    
    # 字符重叠率
    set_a = set(a)
    set_b = set(b)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0


def format_as_markdown(entities, source_file=""):
    """格式化为 Markdown 输出"""
    lines = []
    lines.append("# 实体提取结果")
    lines.append("")
    if source_file:
        lines.append(f"> 源文件：{source_file}")
    lines.append(f"> 提取时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    type_labels = {
        "company": "公司名称",
        "person": "关键人员",
        "date": "日期",
        "amount": "金额/比例",
        "regulation": "法律法规",
        "address": "地址",
    }
    
    for etype, label in type_labels.items():
        items = entities.get(etype, [])
        if not items:
            continue
        
        lines.append(f"## {label}")
        lines.append("")
        
        if etype == "date":
            for item in items:
                lines.append(f"- {item['value']}")
        elif etype == "company":
            for item in items:
                lines.append(f"- {item['value']}")
        elif etype == "regulation":
            for item in items:
                lines.append(f"- 《{item['value']}》")
        else:
            for item in items:
                lines.append(f"- {item['value']}")
        
        lines.append("")
    
    # 统计
    lines.append("## 统计")
    lines.append("")
    for etype, label in type_labels.items():
        count = len(entities.get(etype, []))
        lines.append(f"- {label}：{count}项")
    
    return "\n".join(lines)


def format_as_json(entities):
    """格式化为 JSON 输出"""
    return json.dumps(entities, ensure_ascii=False, indent=2)


# ── CLI ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="NER 实体提取器 — 从风控报告/尽调文档中提取实体"
    )
    parser.add_argument("--input", "-i", type=str, required=True,
                        help="输入文件路径（Markdown/文本格式）")
    parser.add_argument("--output", "-o", type=str,
                        help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--format", "-f", choices=["json", "markdown"], default="json",
                        help="输出格式（默认 json）")
    parser.add_argument("--types", type=str, default="company,person,date,amount,regulation,address",
                        help="提取类型（逗号分隔，默认全部）")
    parser.add_argument("--dedup-threshold", type=float, default=0.8,
                        help="去重相似度阈值（0-1，默认 0.8）")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：文件不存在 {input_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    entity_types = [t.strip() for t in args.types.split(",")]
    entities = extract_entities(text, entity_types, args.dedup_threshold)
    
    if args.format == "markdown":
        output = format_as_markdown(entities, str(input_path))
    else:
        output = format_as_json(entities)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"实体提取完成: {output_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
