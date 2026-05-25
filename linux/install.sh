#!/bin/bash
# install.sh — Hermes 记忆系统 Linux 安装脚本
set -e

echo "=== Hermes Memory System for Linux ==="

# 检测 HERMES_HOME
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
echo "HERMES_HOME = $HERMES_HOME"

# 创建目录
mkdir -p "$HERMES_HOME/scripts/prompts"
mkdir -p "$HERMES_HOME/memory/backups"
mkdir -p "$HERMES_HOME/memories"

# 复制脚本
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)/scripts"
PROMPT_DIR="$(cd "$(dirname "$0")" && pwd)/prompts"

cp "$SCRIPT_DIR/hot-memory-bridge.py" "$HERMES_HOME/scripts/"
cp "$SCRIPT_DIR/vector-indexer.py" "$HERMES_HOME/scripts/"
cp "$SCRIPT_DIR/auto_memory.py" "$HERMES_HOME/scripts/"
cp "$SCRIPT_DIR/auto_memory_context_refresh.py" "$HERMES_HOME/scripts/"
cp "$SCRIPT_DIR/memory-capacity-check.py" "$HERMES_HOME/scripts/"
cp "$SCRIPT_DIR/fact_extract_prompt.md" "$HERMES_HOME/scripts/"
cp "$SCRIPT_DIR/memory_usage_check.py" "$HERMES_HOME/scripts/"
cp "$PROMPT_DIR/semantic-indexer.md" "$HERMES_HOME/scripts/prompts/"

chmod +x "$HERMES_HOME/scripts/"*.sh 2>/dev/null || true

echo "Scripts copied to $HERMES_HOME/scripts/"

# 确认数据库
if [ ! -f "$HERMES_HOME/sqlitemem.db" ]; then
    echo "Warning: $HERMES_HOME/sqlitemem.db not found"
    echo "  Ensure Hermes has been run to generate the database"
fi

# 安装 Python 依赖
echo ""
echo "=== Installing Python dependencies ==="

# 检测可用 pip（优先用 Hermes venv，兼容 externally managed 系统）
PIP="pip3"
if [ -f "$HERMES_HOME/hermes-agent/venv/bin/pip3" ]; then
    PIP="$HERMES_HOME/hermes-agent/venv/bin/pip3"
elif [ -f "$HERMES_HOME/hermes-agent/venv/bin/pip" ]; then
    PIP="$HERMES_HOME/hermes-agent/venv/bin/pip"
fi
# 用户可通过环境变量 PIP_PATH 覆盖
PIP="${PIP_PATH:-$PIP}"

$PIP install sentence-transformers numpy --quiet 2>/dev/null && \
    echo "OK: sentence-transformers + numpy installed" || \
    echo "Warning: auto-install failed, try: $PIP install sentence-transformers numpy"

# torch 按需安装（CPU 版即可）
python3 -c "import torch" 2>/dev/null || \
    $PIP install torch --quiet 2>/dev/null && \
    echo "OK: torch installed" || \
    echo "Warning: torch auto-install failed, try: $PIP install torch"

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. First-time vector index: python $HERMES_HOME/scripts/vector-indexer.py index"
echo "  2. Register cron jobs (see README.md)"
echo "  3. Verify: python $HERMES_HOME/scripts/vector-indexer.py stats"
