"""validate_delivery 的 PASS/FAIL 固定样例与 docx 小样转换。"""
import json
import subprocess
import sys

OUTPUT_JSON_MIN = {
    "skill": "risk-report",
    "version": "6.2",
    "project": "t",
    "date": "2026-09-18",
    "status": "completed",
    "outputs": ["04_risk_report/report_final.md", "04_risk_report/risk_matrix.json"],
}


def _run(repo_root, project_dir):
    return subprocess.run(
        [sys.executable, "scripts/validate_delivery.py", str(project_dir)],
        cwd=repo_root, capture_output=True, text=True,
    )


def test_validate_delivery_empty_project_passes_with_skips(repo_root, tmp_path):
    """空项目（未执行任何 Phase）应 PASS/WARN 退出 0，不得 FAIL。"""
    proj = tmp_path / "empty_proj"
    proj.mkdir()
    r = _run(repo_root, proj)
    assert r.returncode == 0, r.stdout + r.stderr


def test_validate_delivery_completed_phase_missing_artifact_fails(repo_root, tmp_path):
    """声明 completed 但缺必须产物 → FAIL → exit 1。"""
    proj = tmp_path / "bad_proj"
    phase = proj / "04_risk_report"
    phase.mkdir(parents=True)
    (phase / "output.json").write_text(
        json.dumps(OUTPUT_JSON_MIN, ensure_ascii=False), encoding="utf-8"
    )
    r = _run(repo_root, proj)
    assert r.returncode == 1, "缺报告正文与 risk_matrix 应 FAIL"
    assert "FAIL" in r.stdout


def test_validate_delivery_completed_phase_with_artifacts(repo_root, tmp_path):
    """04 阶段补齐报告与矩阵（编号一致）应无 FAIL。"""
    proj = tmp_path / "good_proj"
    phase = proj / "04_risk_report"
    phase.mkdir(parents=True)
    (phase / "output.json").write_text(
        json.dumps(OUTPUT_JSON_MIN, ensure_ascii=False), encoding="utf-8"
    )
    (phase / "report_final.md").write_text(
        "# 风控报告（样例）\n\nR01 股权代持线索：见 01 清单。\n", encoding="utf-8"
    )
    (phase / "risk_matrix.json").write_text(json.dumps(
        {"risks": [{"risk_id": "R01", "title": "股权代持线索", "level": "高"}]},
        ensure_ascii=False, indent=2,
    ), encoding="utf-8")
    r = _run(repo_root, proj)
    assert "FAIL 0" in r.stdout or "FAIL: 0" in r.stdout or r.returncode == 0, r.stdout
    assert r.returncode == 0


def test_docx_engine_small_conversion(repo_root, tmp_path):
    docx = pytest_import_docx_or_skip()
    src = tmp_path / "mini.md"
    src.write_text(
        "# 标题\n\n第一段正文。\n\n| A | B |\n|---|---|\n| 1 | 2 |\n",
        encoding="utf-8",
    )
    out = tmp_path / "mini.docx"
    r = subprocess.run(
        [sys.executable, "-m", "docx_engine.cli", "--input", str(src), "--output", str(out)],
        cwd=repo_root / "scripts", capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.exists() and out.stat().st_size > 0


def pytest_import_docx_or_skip():
    import pytest
    try:
        import docx  # noqa: F401
    except ImportError:
        import pytest as _p
        pytest.skip("python-docx 未安装（requirements/core.txt）")
