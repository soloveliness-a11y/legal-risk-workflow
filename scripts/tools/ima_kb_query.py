#!/usr/bin/env python3
"""
IMA 知识库 AI 问答工具 V3.0（兼容入口）

⚠️  本文件现为兼容层，浏览器 session 管理已迁移至 infra/browser_session.py。
    IMA 页面操作逻辑保留在本文件（与 IMA DOM 结构强耦合，不适合进一步拆分）。

用法（不变）：
  python3 ima_kb_query.py <知识库名> <问题> [--model MODEL]
  python3 ima_kb_query.py --list-kbs
  python3 ima_kb_query.py --save-session
"""

import sys
import os
import json
import argparse
import time
import re
from pathlib import Path
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from infra.browser_session import (
    launch_browser, new_context, navigate_and_restore,
    save_session, save_local_storage, is_logged_in, interactive_login,
    SESSION_DIR,
)
from config_loader import get_config

_cfg = get_config()
IMA_URL = _cfg.get("ima.base_url", "https://ima.qq.com")
_DEFAULT_MODEL = _cfg.get("ima.default_model", "glm-deep")
_QUERY_TIMEOUT = _cfg.get("ima.query_timeout", 120)

MODEL_MAP = {
    "glm-deep": {"series": "智谱 GLM-5.1", "mode": "深度"},
    "glm":      {"series": "智谱 GLM-5.1", "mode": "快速"},
    "ds-deep":  {"series": "DeepSeek V3.2", "mode": "深度"},
    "ds":       {"series": "DeepSeek V3.2", "mode": "快速"},
    "hy-deep":  {"series": "Tencent Hy3 preview", "mode": "深度"},
    "hy":       {"series": "Tencent Hy3 preview", "mode": "快速"},
}
DEFAULT_MODEL = _DEFAULT_MODEL


# ── IMA 页面操作（与 DOM 强耦合，保留在本文件）─────────────────────

def click_model_selector(page) -> str | None:
    """点击模型选择器按钮，返回当前显示的模型文字"""
    result = page.evaluate("""() => {
        const all = document.querySelectorAll('*');
        for (const el of all) {
            const cls = el.className || '';
            if (typeof cls === 'string' && cls.includes('_modelSelectionText') && el.offsetParent !== null) {
                const text = el.textContent.trim();
                if (text && text.length > 0 && text.length < 40) {
                    el.click();
                    return text;
                }
            }
        }
        for (const el of all) {
            const cls = el.className || '';
            if (typeof cls === 'string' && cls.includes('_modelWrap') && el.offsetParent !== null) {
                const text = el.textContent.trim();
                if (text && text.length > 0 && text.length < 40) {
                    el.click();
                    return text;
                }
            }
        }
        return null;
    }""")
    return result


def select_series(page, series_name: str) -> bool:
    """在模型下拉面板中选择模型系列"""
    time.sleep(0.8)
    found = page.evaluate(f"""() => {{
        const target = '{series_name}';
        const all = document.querySelectorAll('*');
        for (const el of all) {{
            const cls = el.className || '';
            if (typeof cls === 'string' && cls.includes('_name_') && el.offsetParent !== null) {{
                const text = el.textContent.trim();
                if (text === target) {{
                    el.click();
                    return true;
                }}
            }}
        }}
        for (const el of all) {{
            const text = el.textContent.trim();
            if (el.offsetParent !== null && el.children.length === 0 && text === target) {{
                el.click();
                return true;
            }}
        }}
        for (const el of all) {{
            const text = el.textContent.trim();
            if (el.offsetParent !== null && el.children.length === 0 &&
                text.length > 2 && text.length < 40 && target.includes(text)) {{
                el.click();
                return true;
            }}
        }}
        return false;
    }}""")
    if found:
        print(f"    ✅ 选中系列: {series_name}", file=sys.stderr)
    else:
        print(f"    ❌ 未找到系列: {series_name}", file=sys.stderr)
    return found


def select_mode(page, mode_name: str) -> bool:
    """选择快速/深度模式按钮"""
    time.sleep(0.5)
    found = page.evaluate(f"""() => {{
        const target = '{mode_name}';
        const all = document.querySelectorAll('*');
        for (const el of all) {{
            const cls = el.className || '';
            if (typeof cls === 'string' && cls.includes('_thinkModeBtn') && el.offsetParent !== null) {{
                const text = el.textContent.trim();
                if (text === target) {{
                    el.click();
                    return true;
                }}
            }}
        }}
        for (const el of all) {{
            const text = el.textContent.trim();
            if (el.offsetParent !== null && el.children.length === 0 &&
                (text === target || text === target + '思考')) {{
                el.click();
                return true;
            }}
        }}
        return false;
    }}""")
    if found:
        print(f"    ✅ 选中模式: {mode_name}", file=sys.stderr)
    else:
        print(f"    ⚠️ 未找到模式按钮: {mode_name}", file=sys.stderr)
    return found


def switch_model(page, model_alias: str) -> bool:
    """切换模型（两步：先选快速/深度模式 → 再选系列）"""
    config = MODEL_MAP.get(model_alias, MODEL_MAP[DEFAULT_MODEL])
    series = config["series"]
    mode = config["mode"]

    print(f"  目标: {series} / {mode}", file=sys.stderr)

    current = click_model_selector(page)
    if not current:
        print(f"  ⚠️ 未找到模型选择器按钮", file=sys.stderr)
        return False

    print(f"  当前显示: {current}", file=sys.stderr)
    time.sleep(1.0)

    mode_ok = select_mode(page, mode)
    if not mode_ok:
        print(f"  ⚠️ 模式选择失败，将使用当前模式", file=sys.stderr)

    if not select_series(page, series):
        page.keyboard.press("Escape")
        time.sleep(0.3)
        return False

    time.sleep(1.0)
    page.keyboard.press("Escape")
    time.sleep(0.3)

    new_display = page.evaluate("""() => {
        const all = document.querySelectorAll('*');
        for (const el of all) {
            const cls = el.className || '';
            if (typeof cls === 'string' && cls.includes('_modelSelectionText') && el.offsetParent !== null) {
                return el.textContent.trim();
            }
        }
        return null;
    }""")
    if new_display:
        print(f"  📋 切换后显示: {new_display}", file=sys.stderr)

    print(f"  ✅ 模型切换完成", file=sys.stderr)
    return True


def at_select_kb(page, kb_name: str) -> bool:
    """在编辑器中输入 @ 并选择知识库"""
    editor = page.query_selector("div.tiptap.ProseMirror")
    if not editor:
        print("❌ 找不到编辑器", file=sys.stderr)
        return False

    editor.click()
    time.sleep(0.5)
    page.keyboard.press("@")
    time.sleep(2)

    clicked = page.evaluate(f"""() => {{
        const target = '{kb_name}';
        const all = document.querySelectorAll('*');
        for (const el of all) {{
            if (el.offsetParent !== null && el.children.length === 0 && el.textContent.trim() === target) {{
                el.click();
                return 'exact: ' + el.className.substring(0, 40);
            }}
        }}
        for (const el of all) {{
            const t = el.textContent.trim();
            if (el.offsetParent !== null && el.children.length === 0 && t && target.includes(t) && t.length > 1) {{
                el.click();
                return 'fuzzy: ' + t;
            }}
        }}
        for (const el of all) {{
            const t = el.textContent.trim();
            if (el.offsetParent !== null && el.children.length === 0 && t.includes(target) && t.length < 50) {{
                el.click();
                return 'contains: ' + t;
            }}
        }}
        return null;
    }}""")

    if clicked:
        print(f"  ✅ 已选择知识库: {clicked}", file=sys.stderr)
        time.sleep(1)
        return True
    else:
        print(f"  ❌ 未找到知识库: {kb_name}", file=sys.stderr)
        page.keyboard.press("Escape")
        return False


def type_question_and_send(page, question: str):
    """输入问题并发送"""
    page.keyboard.type(question, delay=30)
    time.sleep(0.5)
    page.keyboard.press("Enter")
    print(f"📤 已发送问题", file=sys.stderr)


def wait_for_answer(page, timeout: int = None) -> str | None:
    """等待 AI 回答完成"""
    timeout = timeout or _QUERY_TIMEOUT
    print(f"⏳ 等待回答（超时 {timeout}s）...", file=sys.stderr)

    start = time.time()
    last_len = 0
    stable_count = 0

    while time.time() - start < timeout:
        time.sleep(3)
        try:
            info = page.evaluate("""() => {
                try {
                    const body = document.body.innerText;
                    return { bodyLen: body.length, ok: true };
                } catch(e) {
                    return { bodyLen: 0, ok: false, error: e.message };
                }
            }""")
        except Exception as e:
            print(f"  ⚠️ JS evaluate 失败: {e}", file=sys.stderr)
            continue

        body_len = info.get("bodyLen", 0)
        elapsed = int(time.time() - start)

        if body_len > 0:
            print(f"  [{elapsed}s] body={body_len}", file=sys.stderr)

        if body_len == last_len and body_len > 1500:
            stable_count += 1
            if stable_count >= 8:
                print(f"  ✅ 内容稳定，回答完成（耗时 {elapsed}s）", file=sys.stderr)
                break
        else:
            stable_count = 0

        last_len = body_len

    return extract_answer(page)


def extract_answer(page) -> str | None:
    """提取 AI 回答文本"""
    answer = page.evaluate("""() => {
        const body = document.body.innerText;
        const endMarkers = ['内容由AI生成仅供参考', '对话模式', '内容由 AI 生成'];
        const lines = body.split('\\n');
        let answerStart = -1;
        let answerEnd = -1;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line === 'ima' && i + 1 < lines.length && lines[i+1].includes('找到')) {
                answerStart = i;
            }
        }

        if (answerStart >= 0) {
            for (let i = answerStart + 1; i < lines.length; i++) {
                const line = lines[i].trim();
                for (const em of endMarkers) {
                    if (line.includes(em)) { answerEnd = i; break; }
                }
                if (answerEnd >= 0) break;
            }
            const end = answerEnd >= 0 ? answerEnd : lines.length;
            const answerLines = lines.slice(answerStart + 1, end);
            const answer = answerLines.join('\\n').trim();
            if (answer.length > 20) return answer;
        }

        for (let i = 0; i < lines.length; i++) {
            if (lines[i].includes('找到了') && lines[i].includes('资料')) {
                let end = lines.length;
                for (let j = i + 1; j < lines.length; j++) {
                    const line = lines[j].trim();
                    for (const em of endMarkers) {
                        if (line.includes(em)) { end = j; break; }
                    }
                    if (end < lines.length) break;
                    if (line.startsWith('@') && j > i + 3) { end = j; break; }
                }
                const answer = lines.slice(i + 1, end).join('\\n').trim();
                if (answer.length > 20) return answer;
            }
        }

        for (let i = 0; i < lines.length; i++) {
            if (lines[i].includes('@') && lines[i].length < 30) {
                let end = lines.length;
                for (let j = i + 1; j < lines.length; j++) {
                    const line = lines[j].trim();
                    for (const em of endMarkers) {
                        if (line.includes(em)) { end = j; break; }
                    }
                    if (end < lines.length) break;
                }
                if (end - i > 2) {
                    return lines.slice(i + 1, end).join('\\n').trim();
                }
            }
        }

        return null;
    }""")
    return answer


# ── API 方式列出知识库 ────────────────────────────────────────────

def list_kbs_via_api():
    """通过 IMA OpenAPI 列出知识库"""
    client_id = os.environ.get("IMA_OPENAPI_CLIENTID", "")
    api_key = os.environ.get("IMA_OPENAPI_APIKEY", "")

    if not client_id:
        cid_file = Path.home() / ".config/ima/client_id"
        if cid_file.exists():
            client_id = cid_file.read_text().strip()
    if not api_key:
        key_file = Path.home() / ".config/ima/api_key"
        if key_file.exists():
            api_key = key_file.read_text().strip()

    if not client_id or not api_key:
        print("❌ 缺少 IMA API 凭证")
        return

    import urllib.request
    url = "https://ima.qq.com/openapi/wiki/v1/search_knowledge_base"
    body = json.dumps({"query": "", "cursor": "", "limit": 50}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("ima-openapi-clientid", client_id)
    req.add_header("ima-openapi-apikey", api_key)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("code") == 0:
                kbs = data["data"].get("info_list", [])
                print(f"📚 IMA 知识库列表（共 {len(kbs)} 个）\n")
                for kb in kbs:
                    print(f"  {kb['kb_name']}")
            else:
                print(f"❌ API 错误: {data.get('msg', 'unknown')}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")


# ── CLI 子命令 ────────────────────────────────────────────────────

def cmd_save_session():
    """交互式扫码登录"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        interactive_login(p, IMA_URL)


def cmd_check_login():
    """检查登录状态"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = launch_browser(p)
        ctx = new_context(browser)
        page = ctx.new_page()
        navigate_and_restore(page, IMA_URL)
        ok = is_logged_in(page)
        print("✅ 登录状态正常" if ok else "❌ Session 已过期，请运行 --save-session 重新登录")
        browser.close()
        return ok


def cmd_query(kb_name: str, question: str, model: str = None, web_search: bool = False, timeout: int = None):
    """执行知识库提问"""
    model = model or DEFAULT_MODEL
    timeout = timeout or _QUERY_TIMEOUT
    from playwright.sync_api import sync_playwright

    model_config = MODEL_MAP.get(model, MODEL_MAP[DEFAULT_MODEL])
    model_display = f"{model_config['series']} / {model_config['mode']}"

    cookie_file = SESSION_DIR / "cookies.json"
    if not cookie_file.exists():
        print("❌ 未找到 session，请先运行 --save-session", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser = launch_browser(p)
        ctx = new_context(browser)
        page = ctx.new_page()

        try:
            print("🌐 打开 IMA...", file=sys.stderr)
            navigate_and_restore(page, IMA_URL)

            if not is_logged_in(page):
                print("❌ Session 过期，请运行 --save-session", file=sys.stderr)
                sys.exit(1)

            print("✅ 已登录", file=sys.stderr)
            print(f"🤖 切换模型到: {model_display}", file=sys.stderr)
            switch_model(page, model)

            print(f"📚 选择知识库: {kb_name}", file=sys.stderr)
            if not at_select_kb(page, kb_name):
                print(f"❌ 无法选择知识库 '{kb_name}'", file=sys.stderr)
                sys.exit(1)

            print(f"❓ 问题: {question}", file=sys.stderr)
            type_question_and_send(page, question)

            answer = wait_for_answer(page, timeout)

            save_session(ctx)
            save_local_storage(page)

            if answer:
                print("\n" + "═" * 60)
                print(f"📚 知识库: {kb_name}")
                print(f"🤖 模型: {model_display}")
                print(f"❓ 问题: {question}")
                print("═" * 60)
                print(answer)
                print("═" * 60)

                result = {
                    "kb": kb_name,
                    "model": model_display,
                    "question": question,
                    "answer": answer,
                    "timestamp": datetime.now().isoformat(),
                }
                print("\n###JSON_OUTPUT###")
                print(json.dumps(result, ensure_ascii=False))
            else:
                print("⚠️ 未能提取到回答文本", file=sys.stderr)
                body = page.inner_text("body")
                print(f"\n=== 页面全文 (debug) ===\n{body[:3000]}", file=sys.stderr)

            return answer

        except Exception as e:
            page.screenshot(path="/tmp/ima_debug_error.png")
            print(f"❌ 错误: {e}", file=sys.stderr)
            raise
        finally:
            browser.close()


# ── CLI 入口 ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="IMA 知识库 AI 问答工具 V3.0")
    parser.add_argument("kb", nargs="?", help="知识库名称")
    parser.add_argument("question", nargs="?", help="问题")
    parser.add_argument("--list-kbs", action="store_true", help="列出所有知识库")
    parser.add_argument("--check-login", action="store_true", help="检查登录状态")
    parser.add_argument("--save-session", action="store_true", help="扫码登录并保存session")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODEL_MAP.keys()),
                        help=f"模型 (默认: {DEFAULT_MODEL})")
    parser.add_argument("--web", action="store_true", help="开启联网搜索")
    parser.add_argument("--timeout", type=int, default=120, help="等待回答超时秒数")

    args = parser.parse_args()

    if args.list_kbs:
        list_kbs_via_api()
        print(f"\n🤖 可用模型:")
        for alias, cfg in MODEL_MAP.items():
            tag = " (默认)" if alias == DEFAULT_MODEL else ""
            print(f"  {alias:10s} → {cfg['series']} / {cfg['mode']}{tag}")
        return

    if args.save_session:
        cmd_save_session()
        return

    if args.check_login:
        cmd_check_login()
        return

    if not args.kb or not args.question:
        parser.print_help()
        sys.exit(1)

    cmd_query(args.kb, args.question, args.model, args.web, args.timeout)


if __name__ == "__main__":
    main()
