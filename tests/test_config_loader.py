"""config_loader 类型化读取与环境变量转换。"""
import os
import textwrap

from config_loader import Config, get_config


def _fresh_config(monkeypatch, tmp_path, body=None, no_file=True):
    """构造无 config 文件干扰的 Config 实例。"""
    if no_file:
        monkeypatch.chdir(tmp_path)
        import config_loader
        monkeypatch.setattr(config_loader, "_instance", None)
        monkeypatch.setattr(config_loader, "_YAML_AVAILABLE", False)
        monkeypatch.setattr(config_loader, "_find_config_file", lambda: None)
        return config_loader.get_config(reload=True)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(textwrap.dedent(body), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    import config_loader
    monkeypatch.setattr(config_loader, "_instance", None)
    monkeypatch.setattr(config_loader, "_find_config_file", lambda: str(cfg))
    return config_loader.get_config(reload=True)


def test_get_bool_env_false_strings(monkeypatch, tmp_path):
    cfg = _fresh_config(monkeypatch, tmp_path)
    for val in ("false", "0", "no", "off", "FALSE", ""):
        monkeypatch.setenv("IMA_SSL_VERIFY", val)
        assert cfg.get_bool("ima.ssl_verify", True) is False, f"环境变量 {val!r} 应转为 False"
    for val in ("true", "1", "yes", "on"):
        monkeypatch.setenv("IMA_SSL_VERIFY", val)
        assert cfg.get_bool("ima.ssl_verify", False) is True, f"环境变量 {val!r} 应转为 True"


def test_get_bool_default(monkeypatch, tmp_path):
    monkeypatch.delenv("IMA_SSL_VERIFY", raising=False)
    cfg = _fresh_config(monkeypatch, tmp_path)
    assert cfg.get_bool("ima.ssl_verify", True) is True
    assert cfg.get_bool("ima.ssl_verify", False) is False


def test_get_int_coercion(monkeypatch, tmp_path):
    cfg = _fresh_config(monkeypatch, tmp_path)
    monkeypatch.setenv("BROWSER_PAGE_TIMEOUT", "15000")
    assert cfg.get_int("browser.page_timeout", 30000) == 15000
    monkeypatch.setenv("BROWSER_PAGE_TIMEOUT", "abc")
    assert cfg.get_int("browser.page_timeout", 30000) == 30000  # 非法值回退默认


def test_get_path_expands_home(monkeypatch, tmp_path):
    cfg = _fresh_config(monkeypatch, tmp_path)
    monkeypatch.setenv("IMA_SESSION_DIR", "~/somewhere/session")
    val = cfg.get_path("ima.session_dir", "~/.config/ima/session")
    assert "~" not in val and val.startswith(os.path.expanduser("~"))


def test_yaml_config_bool_not_string(monkeypatch, tmp_path):
    body = """
    ima:
      ssl_verify: false
      api_timeout: 45
    """
    cfg = _fresh_config(monkeypatch, tmp_path, body=body, no_file=False)
    # yaml 解析时 false 即布尔 False；get_bool 不得把布尔当 truthy 字符串
    assert cfg.get_bool("ima.ssl_verify", True) is False
    assert cfg.get_int("ima.api_timeout", 30) == 45
