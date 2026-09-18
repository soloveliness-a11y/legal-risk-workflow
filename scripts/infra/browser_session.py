"""
浏览器 Session 管理基座

职责：
  - Playwright 浏览器启动（Edge / Chromium）
  - 代理自动检测（sing-box / v2rayN / 环境变量）
  - Session 持久化（cookies + localStorage 读写）
  - 登录状态检查

被谁用：ima_kb_query.py、任何未来需要浏览器自动化的脚本
"""

import json
import os
import socket
import sys
import time
from pathlib import Path

# ── 加载集中配置 ──
_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
from config_loader import get_config

_cfg = get_config()
CONFIG_DIR = Path(_cfg.get_path("ima.config_dir", "~/.config/ima")).expanduser()
# 会话目录独立配置（cookies/localStorage 属敏感凭据，路径与权限单独管理）
SESSION_DIR = Path(_cfg.get_path("ima.session_dir", str(CONFIG_DIR / "session"))).expanduser()
_PROXY_PORTS_STR = _cfg.get("browser.proxy_ports", "10808,10809,7890,7891")
_PROXY_PORTS = [int(p.strip()) for p in str(_PROXY_PORTS_STR).split(",") if p.strip().isdigit()]
_PAGE_TIMEOUT = _cfg.get_int("browser.page_timeout", 30000)
_LOGIN_TIMEOUT = _cfg.get_int("browser.login_timeout", 300)


def _secure_write(path: Path, data: str):
    """以 0600 权限原子写入敏感文件（先写临时文件再改名）。"""
    session_dir = path.parent
    session_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(session_dir, 0o700)
    except OSError:
        pass
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def detect_proxy() -> dict | None:
    """自动检测系统代理（优先探测实际可用端口）"""
    for port in _PROXY_PORTS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            sock.close()
            return {"server": f"socks5://127.0.0.1:{port}"}
        sock.close()

    try:
        config_path = Path.home() / "Library/Application Support/v2rayN/binConfigs/configPre.json"
        if config_path.exists():
            data = json.loads(config_path.read_text())
            for ib in data.get("inbounds", data.get("listeners", [])):
                if ib.get("type") == "socks":
                    port = ib.get("listen_port")
                    if port:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.3)
                        if sock.connect_ex(("127.0.0.1", port)) == 0:
                            sock.close()
                            return {"server": f"socks5://127.0.0.1:{port}"}
                        sock.close()
    except Exception:
        pass

    for env_var in ["https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
        val = os.environ.get(env_var, "")
        if val:
            return {"server": val}

    return None


def launch_browser(playwright, headless=True, channel="msedge"):
    """启动浏览器（默认 Edge）"""
    proxy = detect_proxy()
    opts = {
        "headless": headless,
        "channel": channel,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if proxy:
        opts["proxy"] = proxy
        print(f"🔗 代理: {proxy['server']}", file=sys.stderr)
    return playwright.chromium.launch(**opts)


def new_context(browser, session_dir=SESSION_DIR):
    """创建带 session 恢复的浏览器上下文"""
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 900},
    )
    cookie_file = session_dir / "cookies.json"
    if cookie_file.exists():
        cookies = json.loads(cookie_file.read_text())
        ctx.add_cookies(cookies)
    return ctx


def navigate_and_restore(page, url, session_dir=SESSION_DIR):
    """导航到目标 URL 并恢复 localStorage"""
    page.goto(url, wait_until="networkidle", timeout=_PAGE_TIMEOUT)
    time.sleep(2)

    ls_file = session_dir / "localStorage.json"
    if ls_file.exists():
        ls_data = json.loads(ls_file.read_text())
        if ls_data:
            page.evaluate(f"""() => {{
                const data = {json.dumps(ls_data)};
                for (const [k, v] of Object.entries(data)) {{
                    try {{ localStorage.setItem(k, v); }} catch(e) {{}}
                }}
            }}""")
            page.reload(wait_until="networkidle", timeout=_PAGE_TIMEOUT)
            time.sleep(3)


def save_session(context, session_dir=SESSION_DIR):
    """保存 cookies（0600 权限，目录 0700）"""
    cookies = context.cookies()
    _secure_write(session_dir / "cookies.json", json.dumps(cookies, indent=2))


def save_local_storage(page, session_dir=SESSION_DIR):
    """保存 localStorage（0600 权限，目录 0700）"""
    ls = page.evaluate("() => JSON.stringify(localStorage)")
    _secure_write(session_dir / "localStorage.json", ls)


def is_logged_in(page) -> bool:
    """检查是否已登录（无登录 iframe = 已登录）"""
    frames = page.frames
    return not any("login" in f.url for f in frames)


def interactive_login(playwright, url, timeout_seconds=None):
    """交互式扫码登录，保存 session"""
    timeout_seconds = timeout_seconds or _LOGIN_TIMEOUT
    browser = launch_browser(playwright, headless=False)
    ctx = new_context(browser)
    page = ctx.new_page()

    navigate_and_restore(page, url)

    if is_logged_in(page):
        print("✅ 已经是登录状态，无需扫码", file=sys.stderr)
        save_session(ctx)
        save_local_storage(page)
        browser.close()
        return True

    print("\n" + "=" * 50, file=sys.stderr)
    print("📱 请在浏览器中扫码登录", file=sys.stderr)
    print("⏳ 登录成功后脚本自动检测...", file=sys.stderr)
    print("=" * 50 + "\n", file=sys.stderr)

    for i in range(timeout_seconds):
        time.sleep(1)
        if is_logged_in(page):
            print("✅ 检测到登录成功！", file=sys.stderr)
            time.sleep(2)
            save_session(ctx)
            save_local_storage(page)
            browser.close()
            return True
        if i > 0 and i % 10 == 0:
            print(f"   等待中...({i}s)", file=sys.stderr)

    print("❌ 超时，请重试", file=sys.stderr)
    browser.close()
    return False
