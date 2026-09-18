"""CLI 冒烟与外传确认门槛。"""
import subprocess
import sys

CORE_CLIS = [
    "scripts/tools/risk_screener.py",
    "scripts/tools/doc_preprocessor.py",
    "scripts/tools/consistency_checker.py",
    "scripts/validate_delivery.py",
    "scripts/tools/paddleocr_api.py",
    "scripts/tools/release_scan.py",
    "scripts/tools/validate_skills.py",
    "scripts/tools/ima_kb_archive.py",
    "scripts/tools/ima_kb_query.py",
    "scripts/tools/qcc_cache_manager.py",
    "scripts/tools/entity_extractor.py",
    "scripts/tools/ic_version_consistency_check.py",
    "scripts/tools/md_to_docx_enhanced.py",
]


def _run(repo_root, *args):
    return subprocess.run(
        [sys.executable, *args], cwd=repo_root, capture_output=True, text=True
    )


def test_cli_help_smoke(repo_root):
    for cli in CORE_CLIS:
        r = _run(repo_root, cli, "--help")
        assert r.returncode == 0, f"{cli} --help 退出码 {r.returncode}\n{r.stderr}"


def test_paddleocr_upload_gate_default_deny(repo_root, tmp_path):
    target = tmp_path / "scan.pdf"
    target.write_bytes(b"%PDF-fake")
    r = _run(repo_root, "scripts/tools/paddleocr_api.py", str(target))
    assert r.returncode == 4, "未带 --allow-external-upload 应拒绝上传（exit 4）"
    assert "未获外传确认" in r.stderr


def test_paddleocr_upload_gate_passes_then_fails_on_missing_file(repo_root, tmp_path):
    r = _run(repo_root, "scripts/tools/paddleocr_api.py",
             str(tmp_path / "not_exist.pdf"), "--allow-external-upload")
    assert r.returncode == 2, "门槛通过后文件不存在应 exit 2"


def test_ima_import_gate_default_deny(repo_root):
    r = _run(repo_root, "scripts/tools/ima_kb_archive.py",
             "--import-urls", "https://example.com/a", "--kb", "测试库")
    assert r.returncode == 4, "未带 --allow-external-send 应拒绝（exit 4）"
    assert "未获外传确认" in r.stderr


def test_risk_screener_on_synthetic_fixture(repo_root, tmp_path):
    out = tmp_path / "card.md"
    r = _run(repo_root, "scripts/tools/risk_screener.py",
             "--qcc-cache", "examples/synthetic-demo/materials/qcc_cache_manual.json",
             "--output", str(out))
    assert r.returncode == 0, r.stderr
    assert out.exists()
    card = out.read_text(encoding="utf-8")
    assert "关注" in card, "初筛卡应输出关注分级"
