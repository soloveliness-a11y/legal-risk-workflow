#!/usr/bin/env python3
"""
HTTP 请求基座模块

职责：
  - 统一 HTTP 请求封装（GET / POST JSON / 文件上传）
  - 重试策略（指数退避，仅对可重试状态码）
  - 超时配置
  - SSL context 管理（支持绕过证书验证）
  - 错误处理标准化

设计原则：
  - 仅依赖 Python 标准库（urllib, json, ssl, base64）
  - 不依赖 requests（减少外部依赖）
  - 无业务逻辑，纯技术基座

被谁使用：
  - paddleocr_api.py     → 文件上传 + API 调用
  - capabilities/ima_archive.py → IMA OpenAPI 调用
  - 未来任何需要 REST API 的脚本

用法示例：
    from infra.api_client import HTTPClient, get_env_or_file

    client = HTTPClient(base_url="https://api.example.com", timeout=30, retries=3)
    client.set_header("Authorization", "token xxx")
    result = client.post_json("v1/endpoint", {"key": "value"})
"""

import base64
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from typing import Optional


class HTTPClient:
    """统一 HTTP 客户端，基于 urllib 标准库封装。"""

    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        retries: int = 3,
        ssl_verify: bool = True,
        default_headers: Optional[dict] = None,
    ):
        """
        Args:
            base_url: API 基础地址（如 https://api.example.com），endpoint 会拼接在此之后
            timeout: 单次请求超时（秒）
            retries: 失败重试次数（仅对 429/502/503/504 和连接错误重试）
            ssl_verify: 是否验证 SSL 证书（False 用于代理环境）
            default_headers: 默认请求头，每次请求自动携带
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(1, retries)
        self.default_headers = dict(default_headers) if default_headers else {}
        self._ssl_ctx: Optional[ssl.SSLContext] = None
        if not ssl_verify:
            print(
                "⚠️  安全警告：SSL 证书验证已禁用（ssl_verify=False）。\n"
                "    本连接不校验服务器身份，API 凭据可能被中间人截获。\n"
                "    仅应在受控代理环境中显式开启（config.yaml 的 ima.ssl_verify 等）。\n",
                file=sys.stderr,
            )
            self._ssl_ctx = ssl.create_default_context()
            self._ssl_ctx.check_hostname = False
            self._ssl_ctx.verify_mode = ssl.CERT_NONE

    # ── 配置 ──────────────────────────────────────────────────────

    def set_header(self, key: str, value: str) -> None:
        """设置默认请求头。"""
        self.default_headers[key] = value

    def set_auth_token(self, token: str, prefix: str = "token") -> None:
        """设置 Authorization 头。prefix 默认为 'token'，也可传 'Bearer'。"""
        self.default_headers["Authorization"] = f"{prefix} {token}"

    # ── 核心请求 ──────────────────────────────────────────────────

    def _make_url(self, endpoint: str) -> str:
        """拼接完整 URL。若 base_url 为空，则 endpoint 需为完整 URL。"""
        endpoint = endpoint.lstrip("/")
        if self.base_url:
            return f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        return endpoint

    def _do_request(self, req: urllib.request.Request) -> dict:
        """执行请求，含重试逻辑。成功返回 JSON dict，失败 raise RuntimeError。"""
        last_error: Optional[str] = None

        for attempt in range(self.retries):
            try:
                kwargs: dict = {"timeout": self.timeout}
                if self._ssl_ctx is not None:
                    kwargs["context"] = self._ssl_ctx

                with urllib.request.urlopen(req, **kwargs) as resp:
                    data = resp.read()
                    if not data:
                        return {}
                    try:
                        return json.loads(data)
                    except json.JSONDecodeError:
                        return {"_raw": data.decode("utf-8", errors="replace")}

            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:300]
                last_error = f"HTTP {e.code}: {body}"
                if e.code in (429, 502, 503, 504):
                    wait = 2 ** attempt
                    print(
                        f"⚠️ 请求失败（{last_error}），{wait}s 后重试 ({attempt + 1}/{self.retries})",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                    continue
                raise RuntimeError(last_error)

            except urllib.error.URLError as e:
                last_error = f"URL错误: {e.reason}"
                wait = 2 ** attempt
                print(
                    f"⚠️ 请求失败（{last_error}），{wait}s 后重试 ({attempt + 1}/{self.retries})",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue

        raise RuntimeError(f"请求失败，已重试 {self.retries} 次: {last_error}")

    # ── 便捷方法 ──────────────────────────────────────────────────

    def post_json(
        self,
        endpoint: str,
        payload: dict,
        extra_headers: Optional[dict] = None,
    ) -> dict:
        """POST JSON 请求。"""
        url = self._make_url(endpoint)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        headers = dict(self.default_headers)
        headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(url, data=data, method="POST")
        for k, v in headers.items():
            req.add_header(k, v)

        return self._do_request(req)

    def get(
        self,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> dict:
        """GET 请求，支持查询参数。"""
        url = self._make_url(endpoint)
        if params:
            query = "&".join(
                f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()
            )
            url = f"{url}?{query}"

        req = urllib.request.Request(url, method="GET")
        for k, v in self.default_headers.items():
            req.add_header(k, v)

        return self._do_request(req)

    def upload_base64(
        self,
        endpoint: str,
        file_path: str,
        field_name: str = "file",
        extra_payload: Optional[dict] = None,
    ) -> dict:
        """读取本地文件，base64 编码后作为 JSON 字段 POST。"""
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        file_data = base64.b64encode(file_bytes).decode("ascii")
        payload = {field_name: file_data}
        if extra_payload:
            payload.update(extra_payload)

        return self.post_json(endpoint, payload)

    @staticmethod
    def read_file_base64(file_path: str) -> str:
        """读取文件并返回 base64 编码字符串（不发送请求）。"""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")


# ── 独立便捷函数（向后兼容 / 简单场景）───────────────────────────


def post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    timeout: int = 30,
    retries: int = 3,
    ssl_verify: bool = True,
) -> dict:
    """单条 POST JSON 便捷函数（无需实例化 HTTPClient）。"""
    client = HTTPClient(base_url="", timeout=timeout, retries=retries, ssl_verify=ssl_verify)
    if headers:
        for k, v in headers.items():
            client.set_header(k, v)
    # url 作为完整地址传入，endpoint 传空字符串
    return client.post_json(url, payload)


def get_env_or_file(
    var_name: str,
    file_path: Optional[str] = None,
    default: str = "",
) -> str:
    """
    读取配置优先级：环境变量 → 文件 → 默认值。

    Args:
        var_name: 环境变量名
        file_path: 配置文件绝对路径（可选）
        default: 默认值
    """
    value = os.environ.get(var_name, "")
    if value:
        return value
    if file_path and os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return default
