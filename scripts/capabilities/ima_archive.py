"""
IMA 知识库归档原子能力

职责：
  - IMA OpenAPI 调用（含凭证读取、SSL 绕过）
  - 知识库查询（ID 查找、列表、内容浏览）
  - URL 批量导入到知识库（支持文件夹）
  - 文件夹自动匹配

依赖：
  - infra/api_client.py → HTTPClient 基座（统一 HTTP 请求封装）

不依赖：浏览器自动化（纯 API 调用）
"""

import json
import os
import re
import sys
from pathlib import Path

# ── 确保能导入 infra 基座 ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ANCESTOR = os.path.join(_SCRIPT_DIR, "..")
for _p in (_SCRIPT_DIR, _ANCESTOR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from infra.api_client import HTTPClient, get_env_or_file
from config_loader import get_config

_cfg = get_config()
CONFIG_DIR = Path(_cfg.get_path("ima.config_dir", "~/.config/ima")).expanduser()
_IMA_BASE_URL = _cfg.get("ima.base_url", "https://ima.qq.com")
_IMA_SSL_VERIFY = _cfg.get_bool("ima.ssl_verify", True)
_IMA_TIMEOUT = _cfg.get_int("ima.api_timeout", 30)


def get_credentials():
    """读取 IMA API 凭证：环境变量 → 配置文件"""
    client_id = get_env_or_file("IMA_OPENAPI_CLIENTID", str(CONFIG_DIR / "client_id"))
    api_key = get_env_or_file("IMA_OPENAPI_APIKEY", str(CONFIG_DIR / "api_key"))

    if not client_id or not api_key:
        print("❌ 缺少 IMA API 凭证")
        sys.exit(1)

    return client_id, api_key


def _make_client(timeout: int | None = None) -> HTTPClient:
    """创建配置好的 IMA HTTPClient 实例。"""
    client_id, api_key = get_credentials()
    client = HTTPClient(
        base_url=_IMA_BASE_URL,
        timeout=timeout or _IMA_TIMEOUT,
        retries=3,
        ssl_verify=_IMA_SSL_VERIFY,
    )
    client.set_header("ima-openapi-clientid", client_id)
    client.set_header("ima-openapi-apikey", api_key)
    return client


def ima_api(endpoint: str, body: dict, timeout: int | None = None) -> dict:
    """调用 IMA OpenAPI（向后兼容的便捷函数）。"""
    client = _make_client(timeout)
    try:
        result = client.post_json(endpoint, body)
        if result.get("code") != 0:
            print(f"⚠️ API 返回非零: {result.get('msg', 'unknown')}", file=sys.stderr)
        return result
    except RuntimeError as e:
        print(f"❌ 请求失败: {e}", file=sys.stderr)
        return {"code": -2, "msg": str(e)}


def find_kb_id(kb_name: str) -> str | None:
    """通过名称查找知识库 ID"""
    result = ima_api("openapi/wiki/v1/search_knowledge_base", {
        "query": kb_name, "cursor": "", "limit": 20
    })
    if result.get("code") != 0:
        return None
    for kb in result.get("data", {}).get("info_list", []):
        if kb["kb_name"] == kb_name:
            return kb["kb_id"]
    for kb in result.get("data", {}).get("info_list", []):
        if kb_name in kb["kb_name"] or kb["kb_name"] in kb_name:
            print(f"  📋 模糊匹配: '{kb['kb_name']}' ← '{kb_name}'", file=sys.stderr)
            return kb["kb_id"]
    return None


def find_folder_id(kb_id: str, folder_name: str) -> str | None:
    """在知识库中查找文件夹ID（media_type=99）"""
    result = ima_api("openapi/wiki/v1/search_knowledge", {
        "query": folder_name,
        "knowledge_base_id": kb_id,
        "cursor": ""
    })
    if result.get("code") != 0:
        return None
    for item in result.get("data", {}).get("info_list", []):
        if item.get("media_type") == 99 and item.get("title") == folder_name:
            return item.get("media_id")
    for item in result.get("data", {}).get("info_list", []):
        if item.get("media_type") == 99 and folder_name in item.get("title", ""):
            return item.get("media_id")
    return None


def list_kbs():
    """列出所有知识库"""
    result = ima_api("openapi/wiki/v1/search_knowledge_base", {
        "query": "", "cursor": "", "limit": 20
    })
    if result.get("code") != 0:
        print(f"❌ 获取知识库列表失败: {result.get('msg', '')}")
        return []
    return result.get("data", {}).get("info_list", [])


def list_kb_content(kb_name: str):
    """列出知识库内容（含文件夹层级）"""
    kb_id = find_kb_id(kb_name)
    if not kb_id:
        print(f"❌ 未找到知识库: {kb_name}")
        return []
    result = ima_api("openapi/wiki/v1/get_knowledge_list", {
        "knowledge_base_id": kb_id, "cursor": "", "limit": 20
    })
    if result.get("code") != 0:
        print(f"❌ 获取内容失败: {result.get('msg', '')}")
        return []
    return result.get("data", {}).get("info_list", [])


def import_urls(urls: list[str], kb_name: str, folder_name: str | None = None) -> dict:
    """导入 URL 到知识库，返回统计结果 {success, fail, details}"""
    if not urls:
        return {"success": 0, "fail": 0, "details": []}

    kb_id = find_kb_id(kb_name)
    if not kb_id:
        print(f"❌ 未找到知识库: {kb_name}")
        return {"success": 0, "fail": 0, "details": []}

    folder_id = None
    if folder_name:
        folder_id = find_folder_id(kb_id, folder_name)
        if folder_id:
            print(f"📁 目标文件夹: {folder_name}")
        else:
            print(f"⚠️ 未找到文件夹 '{folder_name}'，导入到根目录")

    batch_size = 10
    total_success = 0
    total_fail = 0
    details = []

    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        body = {
            "knowledge_base_id": kb_id,
            "urls": batch
        }
        if folder_id:
            body["folder_id"] = folder_id

        result = ima_api("openapi/wiki/v1/import_urls", body)

        if result.get("code") == 0:
            results_dict = result.get("data", {}).get("results", {})
            if results_dict:
                for url_key, info in results_dict.items():
                    if info.get("ret_code") == 0:
                        total_success += 1
                        details.append({"url": url_key, "status": "success"})
                    else:
                        total_fail += 1
                        details.append({"url": url_key, "status": "fail", "reason": info.get("ret_code")})
            else:
                success_list = result.get("data", {}).get("success_list", [])
                fail_list = result.get("data", {}).get("fail_list", [])
                total_success += len(success_list)
                total_fail += len(fail_list)
                for s in success_list:
                    details.append({"url": s, "status": "success"})
                for f in fail_list:
                    details.append({"url": f.get("url", ""), "status": "fail", "reason": f.get("reason", "")})
        else:
            total_fail += len(batch)
            for url in batch:
                details.append({"url": url, "status": "fail", "reason": result.get("msg", "")})

    return {"success": total_success, "fail": total_fail, "details": details}


# ── 文件夹自动匹配 ────────────────────────────────────────────────

FOLDER_RULES: list[tuple[list[str], str]] = [
    (["research", "研究", "ipo", "行业", "调研"], "行业研究"),
    (["专利", "patent", "商标", "trademark", "知识产权", "ipr"], "知识产权"),
    (["增资", "股权转让", "sha", "股东协议", "交易文件", "交易"], "交易文件"),
    (["bp", "商业计划", "pitch"], "公司资料"),
    (["竞业", "职务发明", "专利纠纷", "技术秘密"], "知识产权"),
    (["合规", "数据", "gdpr", "隐私"], "合规监管"),
    (["竞品", "competitor", "对比"], "竞品分析"),
]


def auto_match_folder(file_path: str, kb_id: str) -> str | None:
    """根据文件路径自动匹配知识库中的文件夹"""
    path_lower = file_path.lower()
    for keywords, folder_name in FOLDER_RULES:
        if any(kw in path_lower for kw in keywords):
            folder_id = find_folder_id(kb_id, folder_name)
            if folder_id:
                return folder_name
    return None


# ── URL 提取 ──────────────────────────────────────────────────────

def extract_urls_from_file(file_path: str) -> list[str]:
    """从 markdown 文件中提取所有 HTTP(S) URL"""
    content = Path(file_path).read_text(encoding="utf-8")
    urls = []
    md_links = re.findall(r'\[([^\]]*)\]\((https?://[^\s\)]+)\)', content)
    for text, url in md_links:
        urls.append(url)
    bare_urls = re.findall(r'(?<!\()(https?://[^\s\)\]<>"]+)', content)
    for url in bare_urls:
        if url not in urls:
            urls.append(url)

    seen = set()
    filtered = []
    skip_patterns = [
        'google.com/search', 'baidu.com/s?', 'bing.com/search',
        'localhost', '127.0.0.1', '0.0.0.0',
        'workbuddy', 'codebuddy',
    ]
    for url in urls:
        url = url.rstrip('.,;:)')
        if url in seen:
            continue
        seen.add(url)
        if any(p in url.lower() for p in skip_patterns):
            continue
        filtered.append(url)
    return filtered


def extract_urls_from_sources(sources_path: str) -> list[str]:
    """从 sources_*.json 文件提取 URL"""
    content = Path(sources_path).read_text(encoding="utf-8")
    data = json.loads(content)
    urls = []
    for src in data.get("sources", []):
        url = src.get("url", "")
        if url and url.startswith("http"):
            urls.append(url)
    return urls
