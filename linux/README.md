# Hermes Memory System for Linux (CPU)

将道码的记忆系统（三层架构）部署到 Linux 纯 CPU 环境的适配版。

## 三层搜索架构

```
向量搜索（跨语言语义）→ 语义标签（中文桥）→ FTS5（关键词兜底）
```

## 包含脚本

| 文件 | 说明 | 周期 |
|:----|:----|:----:|
| `scripts/vector-indexer.py` | 向量编码 + 余弦相似度搜索 | 每 60 分钟 |
| `scripts/hot-memory-bridge.py` | SQLite 事实 → MEMORY.md 合并 | 每 30 分钟 |
| `scripts/auto_memory.py` | 自动记忆管理（CRUD + 维护） | 按需 |
| `scripts/auto_memory_context_refresh.py` | 上下文刷新 | 每 15 分钟 |
| `scripts/memory-capacity-check.py` | 记忆容量监测 | 每日 2 次 |
| `scripts/memory_usage_check.py` | 记忆使用率检查 | 每小时 |
| `scripts/fact_extract_prompt.md` | 事实提取 prompt 模板 | cron agent |
| `prompts/semantic-indexer.md` | LLM 生成语义标签 | cron agent |

## 安装

```bash
# 一键安装
bash install.sh

# 或手动：
cp scripts/*.py ~/.hermes/scripts/
cp prompts/*.md ~/.hermes/scripts/prompts/
chmod +x ~/.hermes/scripts/*.py
```

## Cron 注册命令

```bash
# Hot Memory Bridge（每 30 分钟）
hermes cron create --name hot-memory-consolidate \
  --schedule "*/30 * * * *" \
  --script ~/.hermes/scripts/hot-memory-bridge.py \
  --no-agent

# 向量索引（每 60 分钟）
hermes cron create --name vector-indexer \
  --schedule "0 * * * *" \
  --script ~/.hermes/scripts/vector-indexer.py \
  --no-agent

# 记忆容量监测（每日 09:00、21:00）
hermes cron create --name memory-capacity \
  --schedule "0 9,21 * * *" \
  --script ~/.hermes/scripts/memory-capacity-check.py \
  --no-agent
```

## 首次初始化

```bash
# 全量回填向量索引（首次较慢 ~35s）
python ~/.hermes/scripts/vector-indexer.py index
```

> **注意：** Linux 版为纯 CPU 环境。GPU 加速版本见根目录 `scripts/`（自动检测 GPU/CPU，无需配置）。
