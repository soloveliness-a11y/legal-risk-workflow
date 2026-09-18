"""安全基座行为：ssl 默认值、会话文件权限、匿名化扫描器。"""
import os
import stat
import subprocess
import sys

from infra import browser_session
from infra.api_client import HTTPClient


def test_ima_ssl_verify_default_true(repo_root, monkeypatch):
    """ima.ssl_verify 默认必须为 True（安全默认值回归）。"""
    import importlib
    import capabilities.ima_archive as ima_archive
    importlib.reload(ima_archive)
    assert ima_archive._IMA_SSL_VERIFY is True


def test_httpclient_ssl_warns_when_disabled(capsys):
    HTTPClient(ssl_verify=False)
    err = capsys.readouterr().err
    assert "安全警告" in err and "SSL" in err


def test_secure_write_permissions(tmp_path):
    session_dir = tmp_path / "sess"
    browser_session._secure_write(session_dir / "cookies.json", "[]")
    cookies = session_dir / "cookies.json"
    assert cookies.read_text(encoding="utf-8") == "[]"
    mode = stat.S_IMODE(cookies.stat().st_mode)
    assert mode == 0o600, f"文件权限应为 0600，实际 {oct(mode)}"
    dmode = stat.S_IMODE(session_dir.stat().st_mode)
    assert dmode == 0o700, f"目录权限应为 0700，实际 {oct(dmode)}"
    # 无 .tmp 残留（原子写入）
    assert not list(session_dir.glob("*.tmp"))


def test_release_scan_clean_on_repo(repo_root):
    r = subprocess.run(
        [sys.executable, "scripts/tools/release_scan.py", "--root", str(repo_root)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_release_scan_detects_planted_findings(repo_root, tmp_path):
    root = tmp_path / "mini"
    (root / "sub").mkdir(parents=True)
    # 号码与邮箱在测试源码中拆分书写，避免被本仓库自身的发布扫描误报
    planted = "联系人 139" + "12345" + "678，邮箱 some" + "one" + "@exam" + "ple.com"
    (root / "sub" / "note.md").write_text(planted, encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(repo_root / "scripts/tools/release_scan.py"),
         "--root", str(root)],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "手机号" in r.stdout and "邮箱" in r.stdout
    # 默认脱敏：不出现完整号码
    assert ("139" + "12345678") not in r.stdout


def test_release_scan_wordlist_private_words(repo_root, tmp_path):
    root = tmp_path / "mini"
    root.mkdir()
    (root / "a.md").write_text("文中出现了某虚拟敏感词", encoding="utf-8")
    wl = tmp_path / "words.txt"
    wl.write_text("某虚拟敏感词\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(repo_root / "scripts/tools/release_scan.py"),
         "--root", str(root), "--wordlist", str(wl)],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "私有词" in r.stdout
