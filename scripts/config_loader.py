"""
集中配置加载器

用法：
    from config_loader import get_config

    cfg = get_config()                          # 加载 config.yaml
    api_url = cfg.get("paddleocr.api_url")      # 点号分隔路径
    api_url = cfg.get("paddleocr.api_url", default="")  # 带默认值
    pocr = cfg.section("paddleocr")             # 获取整个子配置（dict）

优先级：环境变量 > config.yaml > 代码默认值

配置文件查找顺序：
    1. 工作空间根目录/config.yaml（推荐）
    2. scripts/ 同级目录/config.yaml
"""

import os
import sys
from pathlib import Path
from typing import Any

# ── YAML 加载（兼容无 pyyaml 的场景）──

_YAML_AVAILABLE = False
try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    pass


def _parse_yaml_simple(filepath: str) -> dict:
    """简易 YAML 解析器（无第三方依赖），支持基本键值对和嵌套。
    不支持：多行字符串、列表、行内 flow 语法、锚点等高级特性。
    遇到不支持的行会跳过。
    """
    result: dict = {}
    stack: list[tuple[int, dict]] = [(0, result)]

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip()
            # 跳过空行和注释
            if not stripped or stripped.lstrip().startswith("#"):
                continue

            # 计算缩进
            indent = len(stripped) - len(stripped.lstrip())
            key_val = stripped.strip()

            # 弹出栈中缩进 >= 当前的项
            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()

            # 解析 key: value
            if ":" in key_val:
                k, _, v = key_val.partition(":")
                k = k.strip()
                v = v.strip()

                if not v:
                    # 嵌套节，创建子 dict
                    new_dict: dict = {}
                    parent = stack[-1][1]
                    parent[k] = new_dict
                    stack.append((indent, new_dict))
                else:
                    # 叶子节点
                    parent = stack[-1][1]
                    # 去掉行内注释
                    if " #" in v:
                        v = v[: v.index(" #")].strip()
                    # 类型转换
                    if v.startswith('"') and v.endswith('"'):
                        parent[k] = v[1:-1]
                    elif v == "true":
                        parent[k] = True
                    elif v == "false":
                        parent[k] = False
                    elif v == "null" or v == "~":
                        parent[k] = None
                    else:
                        try:
                            parent[k] = int(v)
                        except ValueError:
                            try:
                                parent[k] = float(v)
                            except ValueError:
                                parent[k] = v

    return result


def _find_config_file() -> str | None:
    """查找 config.yaml 文件"""
    # 1. scripts/ 上级目录（工作空间根目录）
    scripts_dir = Path(__file__).resolve().parent
    workspace_root = scripts_dir.parent
    cfg = workspace_root / "config.yaml"
    if cfg.exists():
        return str(cfg)

    # 2. 当前工作目录
    cfg2 = Path.cwd() / "config.yaml"
    if cfg2.exists():
        return str(cfg2)

    return None


def _load_config_file(filepath: str) -> dict:
    """加载 YAML 配置文件"""
    if _YAML_AVAILABLE:
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # 回退到简易解析器
    return _parse_yaml_simple(filepath)


def _resolve_env(value: Any) -> Any:
    """对字符串值做 ~ 和环境变量展开"""
    if isinstance(value, str):
        # ~ 展开
        if "~" in value:
            value = os.path.expanduser(value)
        # $VAR 或 ${VAR} 环境变量展开
        if "$" in value:
            value = os.path.expandvars(value)
    return value


class Config:
    """配置访问器"""

    def __init__(self, data: dict, source: str = "unknown"):
        self._data = data
        self._source = source

    @property
    def source(self) -> str:
        """配置文件路径"""
        return self._source

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """
        用点号分隔路径获取配置值。
        环境变量优先：先检查 {SECTION}_{KEY} 格式的环境变量。

        例：get("paddleocr.api_url") 先检查 PADDLEOCR_API_URL，再查 config.yaml
        """
        # 环境变量优先
        env_key = dotted_key.upper().replace(".", "_")
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val

        # 从配置字典查找
        keys = dotted_key.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                # 默认值同样做 ~ / 环境变量展开，与配置文件值的处理保持一致
                return _resolve_env(default)

        return _resolve_env(node)

    def section(self, dotted_key: str) -> dict:
        """获取整个子配置节（返回 dict）"""
        keys = dotted_key.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return {}
        return node if isinstance(node, dict) else {}

    # ── 类型化读取（环境变量总是字符串，必须显式转换）────────────────

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        """按布尔语义转换：'false'/'0'/'no'/'off'/'' → False，其余非空 → True。"""
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() not in ("", "false", "0", "no", "off", "null", "none")

    def get_bool(self, dotted_key: str, default: bool = False) -> bool:
        """读取布尔配置。环境变量 IMA_SSL_VERIFY=false 会被正确识别为 False。"""
        val = self.get(dotted_key, default)
        return self._coerce_bool(val)

    def get_int(self, dotted_key: str, default: int = 0) -> int:
        """读取整数配置（环境变量/简单解析器可能给字符串）。"""
        val = self.get(dotted_key, default)
        try:
            return int(str(val).strip())
        except (TypeError, ValueError):
            print(f"⚠️ 配置 {dotted_key}={val!r} 不是整数，使用默认值 {default}", file=sys.stderr)
            return default

    def get_path(self, dotted_key: str, default: str = "") -> str:
        """读取路径配置，统一做 ~ 与环境变量展开后返回字符串。"""
        val = self.get(dotted_key, default)
        val = str(val).strip() if val is not None else ""
        if "~" in val:
            val = os.path.expanduser(val)
        if "$" in val:
            val = os.path.expandvars(val)
        return val

    def require(self, dotted_key: str) -> Any:
        """获取必需的配置项，缺失时报错退出"""
        val = self.get(dotted_key)
        if val is None or val == "":
            print(f"❌ 缺少必需配置项: {dotted_key}", file=sys.stderr)
            print(f"   请在 config.yaml 中设置，或设置环境变量 {dotted_key.upper().replace('.', '_')}",
                  file=sys.stderr)
            sys.exit(1)
        return val

    def raw(self) -> dict:
        """返回原始配置字典"""
        return self._data


# ── 单例 ──

_instance: Config | None = None


def get_config(reload: bool = False) -> Config:
    """
    获取全局配置实例（单例）。

    Args:
        reload: 强制重新加载配置文件
    """
    global _instance
    if _instance is not None and not reload:
        return _instance

    cfg_path = _find_config_file()
    if cfg_path:
        data = _load_config_file(cfg_path)
        _instance = Config(data, source=cfg_path)
    else:
        # 无配置文件，使用空字典（脚本会用代码默认值）
        _instance = Config({}, source="(no config file)")

    return _instance


# ── CLI 入口（调试用）──

if __name__ == "__main__":
    cfg = get_config()
    print(f"📄 配置文件: {cfg.source}")
    print()
    import json
    print(json.dumps(cfg.raw(), indent=2, ensure_ascii=False, default=str))
