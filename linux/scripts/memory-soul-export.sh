#!/bin/bash
# memory-soul-export.sh — Linux 版
# 每周导出记忆为可读 Markdown
python3 "$HOME/.hermes/memory/scripts/export_memory.py"
cd "$HOME/.hermes/memory"
git add -A
git commit -m "export: weekly memory snapshot $(date '+%Y-W%W')" || true
git push origin master || true
