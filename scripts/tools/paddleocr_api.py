#!/usr/bin/env python3
"""
PaddleOCR-VL API 调用脚本

用途：替代 PaddleOCR-VL MCP 工具，通过 API 直调避免中文路径编码问题。
支持 PDF 和图片（jpg/jpeg/png/gif/webp）格式。

用法：
  python paddleocr_api.py <file_path> [--allow-external-upload] [-o output.md] [--json] [--no-save]

参数：
  file_path              输入文件路径（PDF或图片）
  --allow-external-upload 显式确认将文件上传到外部 OCR 服务（必选开关，见下）
  -o, --output           输出 Markdown 文件路径（默认：与输入同目录，后缀改为 .ocr.md）
  --json                 同时输出结构化 JSON 结果到 <output>.json
  --no-save              不保存文件，仅打印到 stdout
  --file-type {auto,0,1} 文件类型：auto=自动检测，0=PDF，1=图片（默认 auto）
  --api-url URL          API 地址（默认从环境变量 PADDLEOCR_API_URL 或 config 读取）
  --token TOKEN          API Token（默认从环境变量 PADDLEOCR_TOKEN 或 config 读取）

数据边界（重要）：
  本脚本会把文件内容完整上传到 config 中配置的外部 OCR 服务。
  S1 敏感材料（合同、员工花名册、财务资料、访谈材料、尽调报告、投资建议书等，
  分级见 SECURITY_PRIVACY.md）禁止经本脚本处理；仅已确认公开可获得的材料
  （公告、监管文件、招股书、工商公示档案等）可在确认后上传。
  运行必须带 --allow-external-upload，或在 config.yaml 中
  设置 paddleocr.allow_upload: true，缺省一律拒绝上传并退出。

环境变量（可选，覆盖 config 值）：
  PADDLEOCR_API_URL      API 地址
  PADDLEOCR_TOKEN        API Token
  PADDLEOCR_ALLOW_UPLOAD 设为 1/true 可替代 --allow-external-upload

退出码：
  0  成功
  1  参数错误
  2  文件读取失败
  3  API 调用失败
  4  未获外传确认，拒绝上传

设计说明：
  - 不依赖任何非标准库（仅用 base64, json, os, sys + infra/api_client.py）
  - 自动检测文件类型（根据扩展名）
  - 路径含中文/空格/特殊字符均无问题（Python open() 原生支持）
  - 输出纯 Markdown 文本，可被下游脚本/技能直接消费
"""

import argparse
import json
import os
import sys

# ── 确保能导入 infra 基座 ──
_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from infra.api_client import HTTPClient, get_env_or_file
from config_loader import get_config

# ── 配置来源优先级：CLI参数 > 环境变量 > config.yaml > 代码默认值 ──
_cfg = get_config()
DEFAULT_API_URL = os.environ.get("PADDLEOCR_API_URL", _cfg.get("paddleocr.api_url", ""))
DEFAULT_TOKEN = os.environ.get("PADDLEOCR_TOKEN", _cfg.get("paddleocr.token", ""))
_PADDLEOCR_TIMEOUT = _cfg.get_int("paddleocr.timeout", 120)
_PADDLEOCR_RETRIES = _cfg.get_int("paddleocr.retries", 3)
_UPLOAD_CONFIRMED_BY_CONFIG = _cfg.get_bool("paddleocr.allow_upload", False)
_S1_POLICY = str(_cfg.get("paddleocr.s1_policy", "deny")).strip().lower()

# ── 文件类型映射 ──
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}


def detect_file_type(file_path: str) -> int:
    """根据文件扩展名自动检测类型。返回 0=PDF, 1=图片"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in PDF_EXTENSIONS:
        return 0
    elif ext in IMAGE_EXTENSIONS:
        return 1
    else:
        print(f"⚠️  无法识别文件扩展名 '{ext}'，默认按 PDF 处理", file=sys.stderr)
        return 0


def call_paddleocr(
    file_path: str,
    file_type: int | None = None,
    api_url: str | None = None,
    token: str | None = None,
) -> dict:
    """
    调用 PaddleOCR-VL API，返回完整 JSON 响应。

    Args:
        file_path: 本地文件路径
        file_type: 0=PDF, 1=图片, None=自动检测
        api_url: API 地址
        token: API Token

    Returns:
        API 返回的 JSON dict

    Raises:
        FileNotFoundError: 文件不存在
        RuntimeError: API 调用失败
    """
    api_url = api_url or get_env_or_file("PADDLEOCR_API_URL", default=DEFAULT_API_URL)
    token = token or get_env_or_file("PADDLEOCR_TOKEN", default=DEFAULT_TOKEN)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if file_type is None:
        file_type = detect_file_type(file_path)

    file_data = HTTPClient.read_file_base64(file_path)

    print(
        f"📄 文件: {os.path.basename(file_path)} ({len(file_data):,} base64 chars, 类型={'PDF' if file_type == 0 else '图片'})",
        file=sys.stderr,
    )

    payload = {
        "file": file_data,
        "fileType": file_type,
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }

    client = HTTPClient(base_url="", timeout=_PADDLEOCR_TIMEOUT, retries=_PADDLEOCR_RETRIES, ssl_verify=True)
    client.set_auth_token(token, prefix="token")

    print(f"⏳ 调用 API...", file=sys.stderr)
    return client.post_json(api_url, payload)


def extract_markdown(api_response: dict) -> list[str]:
    """
    从 API 响应中提取所有页面的 Markdown 文本。

    Returns:
        各页 Markdown 文本列表
    """
    pages = []
    result = api_response.get("result", {})
    layout_results = result.get("layoutParsingResults", [])

    if not layout_results:
        print("⚠️  API 返回结果中无 layoutParsingResults", file=sys.stderr)
        return pages

    for i, res in enumerate(layout_results):
        md_text = res.get("markdown", {}).get("text", "")
        if md_text:
            pages.append(md_text)
        else:
            print(f"⚠️  第 {i} 页无文本内容", file=sys.stderr)

    return pages


def main():
    parser = argparse.ArgumentParser(
        description="PaddleOCR-VL API 调用脚本（替代 MCP 工具）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file_path", help="输入文件路径（PDF 或图片）")
    parser.add_argument("--allow-external-upload", action="store_true",
                        help="确认将文件上传到外部 OCR 服务（必须显式传入）")
    parser.add_argument("-o", "--output", help="输出 Markdown 文件路径")
    parser.add_argument("--json", action="store_true", help="同时保存 JSON 结果")
    parser.add_argument("--no-save", action="store_true", help="不保存文件，仅输出到 stdout")
    parser.add_argument(
        "--file-type",
        choices=["auto", "0", "1"],
        default="auto",
        help="文件类型: auto=自动, 0=PDF, 1=图片",
    )
    parser.add_argument("--api-url", help="API 地址（覆盖默认值）")
    parser.add_argument("--token", help="API Token（覆盖默认值）")

    args = parser.parse_args()

    # 外传确认门槛：文件内容将上传到外部服务，必须显式确认
    if not (args.allow_external_upload or _UPLOAD_CONFIRMED_BY_CONFIG):
        size = os.path.getsize(args.file_path) if os.path.isfile(args.file_path) else "?"
        if _S1_POLICY == "trusted-provider":
            gate_hint = (
                "   当前为信任服务商模式（使用者已核验该服务商保密义务且承诺不用于模型训练）。\n"
                "   确认本文件可交由该服务商处理后，加 --allow-external-upload 重试。"
            )
        else:
            gate_hint = (
                "   确认该文件不属于 S1 敏感材料（合同、员工花名册、财务资料、访谈材料、尽调报告、\n"
                "   投资建议书等；分级见 SECURITY_PRIVACY.md）后，加 --allow-external-upload 重试；\n"
                "   已核验服务商保密与不训练承诺的，可在 config.yaml 设置 paddleocr.s1_policy: trusted-provider。"
            )
        print(
            f"⛔ 未获外传确认：本脚本会把文件内容完整上传到外部 OCR 服务（{args.file_path}，{size} bytes）。\n"
            f"{gate_hint}\n"
            "   或在 config.yaml 设置 paddleocr.allow_upload: true（相当于全局确认，慎用）。\n"
            "   数据边界说明见 SECURITY_PRIVACY.md。",
            file=sys.stderr,
        )
        sys.exit(4)

    if args.allow_external_upload or _UPLOAD_CONFIRMED_BY_CONFIG:
        if _S1_POLICY == "trusted-provider":
            print("⚠️  已确认外传（信任服务商模式）：文件内容将上传到外部 OCR 服务。", file=sys.stderr)
        else:
            print("⚠️  已确认外传：文件内容将上传到外部 OCR 服务。", file=sys.stderr)

    # 解析文件类型
    if args.file_type == "auto":
        file_type = None
    else:
        file_type = int(args.file_type)

    # 调用 API
    try:
        api_response = call_paddleocr(
            file_path=args.file_path,
            file_type=file_type,
            api_url=args.api_url,
            token=args.token,
        )
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(2)
    except RuntimeError as e:
        print(f"❌ API 调用失败: {e}", file=sys.stderr)
        sys.exit(3)

    # 提取 Markdown
    pages = extract_markdown(api_response)
    if not pages:
        print("❌ 未提取到任何文本", file=sys.stderr)
        sys.exit(3)

    # 合并多页
    full_markdown = "\n\n---\n\n".join(pages)

    # 输出
    if args.no_save:
        print(full_markdown)
    else:
        # 确定输出路径
        if args.output:
            output_path = args.output
        else:
            base, _ = os.path.splitext(args.file_path)
            output_path = base + ".ocr.md"

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_markdown)
        print(
            f"✅ Markdown 已保存: {output_path} ({len(full_markdown):,} 字符)",
            file=sys.stderr,
        )

        # 可选：保存 JSON
        if args.json:
            json_path = output_path.rsplit(".", 1)[0] + ".json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(api_response, f, ensure_ascii=False, indent=2)
            print(f"✅ JSON 已保存: {json_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
