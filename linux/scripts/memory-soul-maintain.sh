#!/bin/bash
# memory-soul-maintain.sh — Linux 版
# 记忆灵魂维护入口（cron 调用）
MEM_DIR="$HOME/.hermes/memory"
cd "$MEM_DIR" || exit 1
exec bash "$MEM_DIR/scripts/maintain_memory.sh"
