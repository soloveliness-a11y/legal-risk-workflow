#!/bin/bash
# ======================================================================
# risk-workflow — 首次启动脚本
# 用途：检查运行环境、依赖与仓库完整性（宿主中立，不假定特定 Agent 宿主）
# 使用：bash scripts/first_run.sh
# 要求：macOS/Linux，Python >= 3.10
# 注：包含语法编译与核心 CLI 自检——任一核心项失败即非零退出，不给假绿灯。
#     外部依赖（工商数据源 CLI / OCR / 第二信源）均为可选适配器，
#     缺失时核心工作流（尽调+报告+复核+交易文件审查）仍可用（手工采集模式）。
# ======================================================================

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
}

# 注意：set -e 下计数必须用前置自增 ((++N))——后置 ((N++)) 首次取值为 0 时
# 算术命令返回非零状态，脚本会立即退出
print_ok()   { echo -e "  ${GREEN}✅ $1${NC}"; ((++PASS)); }
print_fail() { echo -e "  ${RED}❌ $1${NC}"; ((++FAIL)); }
print_warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; ((++WARN)); }

# ======================================================================
echo ""
echo -e "${CYAN}🚀 risk-workflow — 环境检查与首次部署${NC}"
echo ""

WORKSPACE=$(cd "$(dirname "$0")/.." && pwd)

# 统一经 config_loader 读取配置（优先级：环境变量 > config.yaml > 默认值）
cfg_get() {
    python3 -c "
import sys
sys.path.insert(0, '$WORKSPACE/scripts')
from config_loader import get_config
v = get_config().get('$1', '$2')
print('' if v is None else v)
" 2>/dev/null
}

# 0. config.yaml 检查
print_header "Step 0/7: 集中配置文件"

if [ -f "$WORKSPACE/config.yaml" ]; then
    print_ok "config.yaml 存在"
else
    print_warn "config.yaml 不存在（仅使用外部适配器时才需要）→ 可从 config.example.yaml 复制"
fi

# 1. Python 检查（需要 >= 3.10，代码使用了 X | Y 类型语法）
print_header "Step 1/7: Python 运行时"

if command -v python3 &>/dev/null; then
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        print_ok "Python: $(python3 --version 2>&1)（≥3.10）"
    else
        print_fail "Python 版本过低（需要 ≥3.10，当前 $(python3 --version 2>&1)）"
    fi
else
    print_fail "Python3 未安装。请安装 Python 3.10+"
fi

# 2. Python 依赖（python-docx 为核心依赖：报告 .docx 输出路径需要）
print_header "Step 2/7: Python 依赖包"

if python3 -c "import docx" 2>/dev/null; then
    print_ok "python-docx 已安装（核心依赖：报告 .docx 输出）"
else
    print_fail "python-docx 未安装（核心依赖）→ 运行: python3 -m pip install python-docx"
fi

# Playwright（IMA脚本需要）
if python3 -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
    print_ok "playwright 已安装"
else
    print_warn "playwright 未安装（第二信源脚本需要，可选）→ 运行: python3 -m pip install playwright && playwright install"
fi

# markitdown（文档解析）
if python3 -c "from markitdown import MarkItDown" 2>/dev/null; then
    print_ok "markitdown 已安装"
else
    print_warn "markitdown 未安装（文档解析需要）→ 运行: python3 -m pip install 'markitdown[docx]'"
fi

# PyYAML（config_loader 推荐依赖）
if python3 -c "import yaml" 2>/dev/null; then
    print_ok "pyyaml 已安装"
else
    print_warn "pyyaml 未安装（config.yaml 解析需要）→ 运行: python3 -m pip install pyyaml"
fi

# 3. 语法编译与核心 CLI 自检（这些失败=核心链路不可用，必须 FAIL）
print_header "Step 3/7: 语法编译与核心 CLI 自检"

if python3 -m compileall -q "$WORKSPACE/scripts" 2>/dev/null; then
    print_ok "compileall: scripts/ 全部通过语法编译"
else
    print_fail "compileall 失败 → 运行 python3 -m compileall -q scripts 定位报错文件"
fi

CORE_CLIS=(
    "scripts/tools/risk_screener.py"
    "scripts/tools/doc_preprocessor.py"
    "scripts/tools/consistency_checker.py"
    "scripts/validate_delivery.py"
    "scripts/tools/paddleocr_api.py"
    "scripts/tools/release_scan.py"
    "scripts/tools/validate_skills.py"
)
for cli in "${CORE_CLIS[@]}"; do
    name=$(basename "$cli")
    if python3 "$WORKSPACE/$cli" --help >/dev/null 2>&1; then
        print_ok "CLI 自检: ${name} --help"
    else
        print_fail "CLI 自检失败: ${cli} --help（核心脚本不可执行）"
    fi
done

if (cd "$WORKSPACE/scripts" && python3 -m docx_engine.cli --help >/dev/null 2>&1); then
    print_ok "CLI 自检: docx_engine.cli --help（报告 docx 输出引擎）"
else
    print_fail "CLI 自检失败: python3 -m docx_engine.cli --help（报告 docx 输出不可用）"
fi

# 4. Node.js 和 QCC CLI
print_header "Step 4/7: Node.js + 企查查 CLI"

NODE_PATH=$(cfg_get qcc.node_path "")
# node_path 兼容两种填法：Node 所在目录，或 node 可执行文件本身的路径；统一归一为目录
NODE_BIN=""
if [ -n "$NODE_PATH" ]; then
    if [ -f "$NODE_PATH" ] && [ -x "$NODE_PATH" ]; then
        NODE_BIN="$NODE_PATH"
        NODE_PATH=$(dirname "$NODE_PATH")
    elif [ -f "$NODE_PATH/node" ]; then
        NODE_BIN="$NODE_PATH/node"
    fi
else
    NODE_BIN=$(command -v node 2>/dev/null || true)
fi

if [ -n "$NODE_BIN" ]; then
    NODE_VER=$("$NODE_BIN" --version 2>&1)
    if [ -n "$NODE_PATH" ]; then
        print_ok "Node.js: $NODE_VER (config: $NODE_PATH)"
    else
        print_ok "Node.js: $NODE_VER (system)"
    fi
else
    print_warn "Node.js 未安装（仅工商数据源 CLI 适配器需要，手工采集模式不受影响）"
fi

# QCC CLI
QCC_PATH="$NODE_PATH"
if [ -z "$QCC_PATH" ]; then
    QCC_PATH=$(dirname "$(command -v node 2>/dev/null)" 2>/dev/null)
fi
if [ -n "$QCC_PATH" ] && PATH="$QCC_PATH:$PATH" command -v qcc &>/dev/null; then
    QCC_VER=$(PATH="$QCC_PATH:$PATH" qcc --version 2>&1 || echo "unknown")
    print_ok "qcc-agent-cli: $QCC_VER"
elif command -v qcc &>/dev/null; then
    QCC_VER=$(qcc --version 2>&1 || echo "unknown")
    print_ok "qcc-agent-cli: $QCC_VER"
else
    print_warn "qcc-agent-cli 未安装（可选适配器）→ 手工采集模式可用，见 qcc-scan SKILL；或 npm install -g qcc-agent-cli"
fi

# QCC 配置（路径可经 qcc.config_file 配置）
QCC_CFG=$(cfg_get qcc.config_file "~/.qcc/config.json")
if [ -f "$QCC_CFG" ]; then
    if grep -q '"authorization"' "$QCC_CFG" 2>/dev/null; then
        print_ok "QCC CLI 配置文件存在 ($QCC_CFG)"
    else
        print_warn "QCC CLI 配置文件存在但可能缺少token → 运行: qcc init --authorization 'Bearer <your-token>'"
    fi
else
    print_warn "QCC CLI 未配置（可选适配器，不影响手工采集模式）"
fi

# 5. 凭证配置（经 config_loader 读取，环境变量优先）
print_header "Step 5/7: API 凭证配置"

# PaddleOCR
POCR_URL=$(cfg_get paddleocr.api_url "")
POCR_TOKEN=$(cfg_get paddleocr.token "")
if [ -n "$POCR_URL" ] && [ -n "$POCR_TOKEN" ]; then
    print_ok "PaddleOCR: 已配置 api_url 与 token"
elif [ -n "$POCR_URL" ] || [ -n "$POCR_TOKEN" ]; then
    print_warn "PaddleOCR: api_url 与 token 需同时配置 → 检查 config.yaml 的 paddleocr 节"
else
    print_warn "PaddleOCR: 未配置（可选）→ 在 config.yaml 的 paddleocr 节填入 api_url 和 token，或设置环境变量 PADDLEOCR_API_URL + PADDLEOCR_TOKEN"
fi

# 第二信源（可选，session 路径可经 ima.session_dir 配置）
IMA_SESSION_DIR=$(cfg_get ima.session_dir "~/.config/ima/session")
if [ -d "$IMA_SESSION_DIR" ]; then
    print_ok "第二信源(IMA) session: 目录存在"
else
    print_warn "第二信源未配置（可选增强，缺失时自动跳过）"
fi

# 6. 工作目录结构
print_header "Step 6/7: 工作目录结构"

REQUIRED_DIRS="scripts templates knowledge-base commands skills"
for dir in $REQUIRED_DIRS; do
    if [ -d "$WORKSPACE/$dir" ]; then
        print_ok "$dir/ 目录存在"
    else
        print_warn "$dir/ 目录不存在"
    fi
done

# 知识库关键文件
KB="$WORKSPACE/knowledge-base"
for f in "VERSION.md" "风控术语表.md" "案例学习笔记/writing_patterns.md" "参考报告库"; do
    if [ -e "$KB/$f" ]; then
        print_ok "knowledge-base/$f 存在"
    else
        print_fail "knowledge-base/$f 缺失"
    fi
done

# 7. Skill 完整性检查（宿主中立：核心是仓库 bundle 自身完整性）
print_header "Step 7/7: Skill 完整性检查"

# 规范校验（Agent Skills specification：name/目录一致、metadata 字符串化）
if python3 "$WORKSPACE/scripts/tools/validate_skills.py" "$WORKSPACE/skills" >/dev/null 2>&1; then
    print_ok "Skill 规范校验: 12/12 通过"
else
    print_fail "Skill 规范校验未通过 → 运行 python3 scripts/tools/validate_skills.py 查看明细"
fi

CORE_SKILLS="risk-workflow dd-prep dd-check dd-interview risk-report report-review txn-docs post-invest-check qcc-scan industry-research legal-research"
for skill in $CORE_SKILLS; do
    if [ -f "$WORKSPACE/skills/$skill/SKILL.md" ]; then
        print_ok "${skill}（bundle）"
    else
        print_fail "skills/$skill/SKILL.md 缺失 → 仓库不完整，请重新克隆或检查完整性"
    fi
done

if [ -f "$WORKSPACE/skills/workflow-retro/SKILL.md" ]; then
    print_ok "workflow-retro（bundle，元技能）"
else
    print_warn "workflow-retro 缺失（可选元技能）"
fi

# 宿主安装目录：仅当用户显式配置 paths.skills_dir 时检查；
# 未注册只影响宿主发现，不决定核心环境成败
HOST_SKILL_DIR=$(cfg_get paths.skills_dir "")
if [ -n "$HOST_SKILL_DIR" ]; then
    unregistered=0
    for skill in $CORE_SKILLS workflow-retro; do
        if [ ! -f "$HOST_SKILL_DIR/$skill/SKILL.md" ]; then
            unregistered=$((unregistered + 1))
        fi
    done
    if [ "$unregistered" -eq 0 ]; then
        print_ok "宿主技能目录已注册全部技能（${HOST_SKILL_DIR}）"
    else
        print_warn "$unregistered 个技能未在宿主目录 $HOST_SKILL_DIR 注册 → 仅影响宿主发现，不影响仓库使用"
    fi
else
    print_warn "未配置 paths.skills_dir，跳过宿主注册检查（技能发现方式由你的 Agent 宿主决定，见 README）"
fi

# ======================================================================
# 汇总
print_header "检查结果汇总"
echo -e "  ${GREEN}通过: $PASS${NC}  ${RED}失败: $FAIL${NC}  ${YELLOW}警告: $WARN${NC}"
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}❌ 存在必须解决的问题，请按上述提示修复后重新运行。${NC}"
    exit 1
elif [ $WARN -gt 0 ]; then
    echo -e "${YELLOW}⚠️  基本环境已就绪，但部分可选功能需要额外配置（见上方⚠️项）。${NC}"
    echo -e "   核心工作流（尽调+报告+复核+交易文件）可正常使用。"
    exit 0
else
    echo -e "${GREEN}✅ 所有检查通过！环境已就绪。${NC}"
    echo ""
    echo -e "  下一步："
    echo -e "  1. 确认 config.yaml 中 API 凭证已正确填入（如使用可选适配器）"
    echo -e "  2. 在你的 Agent 宿主中调用 risk-workflow 技能开始使用"
    echo -e "  3. 详细使用指南 → docs/AI_Agent_Risk_Workflow_分享文档.md"
    exit 0
fi
