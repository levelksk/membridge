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

chmod +x "$HERMES_HOME/scripts/"*.sh

echo "✅ 脚本已复制到 $HERMES_HOME/scripts/"

# 确认数据库
if [ ! -f "$HERMES_HOME/sqlitemem.db" ]; then
    echo "⚠️  未找到 $HERMES_HOME/sqlitemem.db"
    echo "   请确保 Hermes 已运行并生成了数据库"
fi

# 安装 Python 依赖
echo ""
echo "=== 安装 Python 依赖 ==="
pip install sentence-transformers numpy --quiet 2>/dev/null && \
    echo "✅ sentence-transformers + numpy 已安装" || \
    echo "⚠️  自动安装失败，请手动: pip install sentence-transformers numpy"

# torch 按需安装（CPU 版即可，GPU 版自行装）
python3 -c "import torch" 2>/dev/null || \
    pip install torch --quiet 2>/dev/null && \
    echo "✅ torch 已安装" || \
    echo "⚠️  自动安装 torch 失败，请手动: pip install torch"

echo ""
echo "=== 安装完成 ==="
echo ""
echo "下一步："
echo "  1. 首次运行向量索引: python $HERMES_HOME/scripts/vector-indexer.py index"
echo "  2. 注册 cron（见 README.md）"
echo "  3. 验证: python $HERMES_HOME/scripts/vector-indexer.py stats"
