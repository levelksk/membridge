# MemBridge — Three-Layer Memory System for LLM Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20|%20Linux-lightgrey.svg)]()
[![GPU](https://img.shields.io/badge/GPU-CPU%20|%20CUDA-green.svg)]()

> **MemBridge** bridges your LLM agent's short-term memory (context window) with long-term storage (SQLite) through a three-tier architecture: **Vector Search → Semantic Tags → Full-Text Search**.

```
                    ┌─────────────────────────────┐
                    │    MEMORY.md (Hot Layer)     │  ◄── Loaded into every session
                    │       ~5K chars, curated     │
                    └──────────┬──────────────────┘
                               │ hot-memory-bridge (every 30min)
                    ┌──────────▼──────────────────┐
                    │      Three-Tier Search       │
                    │                              │
                    │  🥇 Vector Search (384-dim)  │  Semantic + cross-lingual
                    │  🥈 Semantic Tags (CN/EN)    │  LLM-generated labels
                    │  🥉 FTS5 Keyword Search      │  SQLite built-in
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │   SQLite sqlitemem.db       │  ◄── Infinite archive
                    │   + memory.json (auto_mgr)  │
                    └─────────────────────────────┘
```

## ✨ Features

- **Zero Configuration** — Auto-detects GPU/CPU, Windows/Linux paths
- **Three-Tier Search** — From semantic vectors down to keyword fallback
- **Hot Memory Bridge** — Curates SQLite facts into MEMORY.md every 30min
- **Cross-Platform** — Windows (GPU), Linux (CPU), auto-adapts
- **No External Services** — Pure Python + SQLite. No vector DB, no API calls
- **LLM-Powered Labeling** — semantic-indexer generates CN/EN tags automatically

## 🚀 Quick Start

```bash
# Install dependencies
pip install sentence-transformers numpy

# Clone
git clone https://github.com/levelksk/membridge.git
cd membridge
```

### Linux

```bash
# One-shot install
bash linux/install.sh

# Or manual:
cp scripts/*.py ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/*.py

# Initial vector index (takes ~35s on CPU)
python ~/.hermes/scripts/vector-indexer.py index

# Register cron jobs (via Hermes CLI)
hermes cron create --name hot-memory-consolidate --schedule "*/30 * * * *" --script ~/.hermes/scripts/hot-memory-bridge.py --no-agent
hermes cron create --name vector-indexer --schedule "0 * * * *" --script ~/.hermes/scripts/vector-indexer.py --no-agent
hermes cron create --name memory-capacity --schedule "0 9,21 * * *" --script ~/.hermes/scripts/memory-capacity-check.py --no-agent
```

### Windows

```powershell
# Copy scripts to Hermes scripts dir
copy scripts\*.py %USERPROFILE%\AppData\Local\hermes\scripts\

# Initial vector index (takes ~18s first load on GPU)
python %USERPROFILE%\AppData\Local\hermes\scripts\vector-indexer.py index

# Register cron jobs (via Hermes CLI, same commands)
hermes cron create --name hot-memory-consolidate --schedule "*/30 * * * *" --script ~/AppData/Local/hermes/scripts/hot-memory-bridge.py --no-agent
hermes cron create --name vector-indexer --schedule "0 * * * *" --script ~/AppData/Local/hermes/scripts/vector-indexer.py --no-agent
hermes cron create --name memory-capacity --schedule "0 9,21 * * *" --script ~/AppData/Local/hermes/scripts/memory-capacity-check.py --no-agent
```

## 📁 Structure

```
membridge/
├── scripts/                     # Cross-platform scripts
│   ├── vector-indexer.py        # Vector encoding + cosine search
│   ├── hot-memory-bridge.py     # SQLite → MEMORY.md consolidation
│   ├── auto_memory.py           # Memory CRUD + maintenance
│   ├── auto_memory_context_refresh.py  # Context refresh (cron 15min)
│   ├── memory-capacity-check.py # Capacity monitor
│   ├── memory_usage_check.py    # Memory hygiene check
│   └── fact_extract_prompt.md   # Fact extraction prompt template
├── linux/                       # Linux install bundle
│   ├── install.sh               # One-shot Linux setup
│   ├── README.md                # Linux-specific docs
│   ├── prompts/
│   │   └── semantic-indexer.md  # LLM semantic labeling prompt
│   └── scripts/                 # Linux-ready scripts (same as root)
└── LICENSE
```

## 🔧 Default Paths

| Platform | Hermes Home | SQLite DB | MEMORY.md |
|:---------|:-----------|:----------|:----------|
| Windows  | `~/AppData/Local/hermes` | `sqlitemem.db` | `memories/memory.md` |
| Linux    | `~/.hermes` | `sqlitemem.db` | `memories/memory.md` |

Override with `HERMES_HOME` environment variable.

## 🎮 GPU Support

Auto-detected. No config needed:

```
$ python vector-indexer.py index
  🎮 GPU: NVIDIA GeForce RTX 4070 (8.0GB VRAM)
  ⚙️  Device: CUDA
  🔌 加载模型 paraphrase-multilingual-MiniLM-L12-v2...
```

On CPU-only machines it falls back gracefully:

```
$ python vector-indexer.py index
  💻 GPU 不可用，使用 CPU
  ⚙️  Device: CPU
  🔌 加载模型 paraphrase-multilingual-MiniLM-L12-v2...
```

## 📊 Performance

| Tier | Method | Speed | Coverage |
|:-----|:-------|:-----:|:--------:|
| 🥇 | Vector (384-dim, cross-lingual) | ~3s GPU / ~35s CPU (first load) | 100% |
| 🥈 | Semantic tags (CN/EN bridge) | ~0.1ms | 80%+ |
| 🥉 | FTS5 keyword | ~0.01ms | 100% |

## 📄 License

MIT
