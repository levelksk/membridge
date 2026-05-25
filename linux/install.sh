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
cp "$SCRIPT_DIR/memory-soul-maintain.sh" "$HERMES_HOME/scripts/"
cp "$SCRIPT_DIR/memory-soul-export.sh" "$HERMES_HOME/scripts/"
cp "$PROMPT_DIR/semantic-indexer.md" "$HERMES_HOME/scripts/prompts/"

chmod +x "$HERMES_HOME/scripts/"*.sh

echo "✅ 脚本已复制到 $HERMES_HOME/scripts/"

# 确认数据库
if [ ! -f "$HERMES_HOME/sqlitemem.db" ]; then
    echo "⚠️  未找到 $HERMES_HOME/sqlitemem.db"
    echo "   请确保 Hermes 已运行并生成了数据库"
fi

# 安装 Python 依赖
echo ""
echo "=== 检查 Python 依赖 ==="
python3 -c "import sentence_transformers" 2>/dev/null && \
    echo "✅ sentence-transformers 已安装" || \
    echo "⚠️  pip install sentence-transformers"

python3 -c "import numpy" 2>/dev/null && \
    echo "✅ numpy 已安装" || \
    echo "⚠️  pip install numpy"

python3 -c "import torch" 2>/dev/null && \
    echo "✅ torch 已安装" || \
    echo "⚠️  pip install torch (CPU 版即可)"

echo ""
echo "=== 安装完成 ==="
echo ""
echo "下一步："
echo "  1. 首次运行向量索引: python $HERMES_HOME/scripts/vector-indexer.py index"
echo "  2. 注册 cron（见 README.md）"
echo "  3. 验证: python $HERMES_HOME/scripts/vector-indexer.py stats"
