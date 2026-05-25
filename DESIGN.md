# MemBridge Design

## The Problem

LLM agents have a fundamental memory limitation: their context window holds only the current conversation. Facts learned in session A are gone by session B.

Standard solutions all have hidden costs:

| Approach | Problem |
|:---------|:--------|
| ❌ **Bigger context window** | Dilutes attention, token cost explodes, no curation |
| ❌ **Vector database** | Extra infra, ops burden, embedding model download |
| ❌ **Full history injection** | Token cost × sessions, model can't prioritize |
| ❌ **Separate LLM for extraction** | Extra API calls, context loss, latency |

**MemBridge's answer: layered memory, each layer with its own capacity and purpose.**

## Architecture

```
                    ┌─────────────────────────────┐
                    │    MEMORY.md (Hot Layer)     │  ◄── Injected every session
                    │       ~5K chars, curated     │
                    └──────────┬──────────────────┘
                               │ hot-memory-bridge (every 30 min)
                    ┌──────────▼──────────────────┐
                    │      Three-Tier Search       │
                    │                              │
                    │  🥇 Vector Search (384-dim)  │  Cross-lingual semantic
                    │  🥈 Semantic Tags (CN/EN)    │  LLM-generated labels
                    │  🥉 FTS5 Keyword Search      │  SQLite built-in
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │   SQLite sqlitemem.db       │  ◄── Infinite archive
                    └─────────────────────────────┘
```

### Layer 1: Hot Memory (MEMORY.md)

A curated markdown snippet injected into every agent session. Compact (~5K chars) — just the most important facts.

**Capacity limit is intentional.** Forcing curation makes each byte count. Without it, agents drown in noise.

### Layer 2: Three-Tier Search (on-demand)

| Tier | Method | Speed | What it finds |
|:-----|:-------|:-----:|:-------------|
| 🥇 | **Vector** (384-dim cosine) | ~3s GPU / ~35s CPU (1st load) | Semantic matches across languages |
| 🥈 | **Semantic tags** (LLM-labeled) | ~0.1ms | Tagged facts (CN/EN bridge) |
| 🥉 | **FTS5 keyword** | ~0.01ms | Exact term matches (fallback) |

The vector model (`paraphrase-multilingual-MiniLM-L12-v2`) handles cross-lingual search — query in English, find Chinese facts, and vice versa.

### Layer 3: SQLite Archive

All facts live in `sqlitemem.db` — infinite cold storage. Accessed through:
- SQL queries for structured retrieval
- FTS5 for full-text search
- Vector index for semantic search

## Data Flow

```
User Session
    │
    ├─► MEMORY.md injected ──► Agent has hot facts immediately
    │
    ├─► Agent creates new facts
    │     └─► SQLite (real-time write)
    │
    └─► Cron jobs (background)
          ├─ vector-indexer (60 min) ───► Encodes new entries → vectors table
          ├─ semantic-indexer (60 min) ─► LLM generates CN/EN tags
          ├─ hot-memory-bridge (30 min) ─► Consolidates high-importance facts → MEMORY.md
          └─ memory-extract (30 min) ─────► Scans conversations for new facts
```

### Hot Memory Bridge

The key consolidation loop:

```
SQLite(entries WHERE importance >= 3)
    → Sort by importance desc
    → Trim to ~4K chars (leaves 1K buffer)
    → Write to MEMORY.md
```

This runs every 30 minutes. High-importance facts auto-promote to hot memory. Old, unused facts stay in cold SQLite — available via search but not consuming context.

## Vector Engine

### Model

- **Name:** `paraphrase-multilingual-MiniLM-L12-v2`
- **Dimensions:** 384
- **Size:** ~458MB (on disk)
- **VRAM usage:** ~460MB (GPU)
- **Languages:** 50+ (CN/EN/JP/DE/FR...)
- **License:** Apache 2.0

### GPU Support

Auto-detected at runtime — no configuration needed:

```python
_DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
```

| | First load | Batch encode (32) | Single query |
|:---|:---------:|:-----------------:|:-----------:|
| **GPU (RTX 4070)** | ~18s | ~15ms | <1ms |
| **CPU (32GB RAM)** | ~35s | ~420ms | ~8ms |

> ⚠️ First load is dominated by model deserialization + CUDA kernel warmup, not disk I/O. Restarting the service resets VRAM — next query loads the model again.

### Indexing Strategy

- **Incremental only** — skips entries already in `vectors` table
- **Batch size:** 32 (GPU), 8 (CPU)
- **Storage:** Pickle-serialized float32 numpy arrays in SQLite BLOB column

## Semantic Tags

The `semantic-indexer` cron job uses the LLM agent itself to generate CN/EN tags for unlabeled entries:

```
Input:  "User prefers black-box testing approaches"
Output: {"cn": ["黑盒测试", "测试策略", "质量保障"],
         "en": ["black-box testing", "testing methodology"]}
```

These tags sit in a SQLite `tags` column, indexed by GIN-style LIKE queries. The Chinese-English bridge enables cross-lingual lookup without hitting the vector model.

## Memory Categories

Each fact is classified for efficient retrieval:

| Category | What it stores | Lifespan |
|:---------|:---------------|:---------|
| `pref` | User preferences, habits, style | Permanent |
| `env` | Environment config, tools installed | Medium |
| `fact` | Objective facts (identity, projects) | Long |
| `skill` | Skills learned, tech used | Medium |

## Non-Goals

- **Not a replacement for Hermes built-in memory** — they complement each other
- **Not a vector DB** — SQLite + cosine comparison is good enough for 1K-10K entries
- **Not a multi-agent memory bus** — single-agent scope (for now)

## Why Not...

| Alternative | Why MemBridge doesn't use it |
|:------------|:----------------------------|
| Chroma/Pinecone | Extra dependency, ops burden, overkill for <10K entries |
| Redis | Another process to manage, persistence complexity |
| Embedding-as-a-Service | Latency, cost, offline requirement |
| PostgreSQL pgvector | Overkill for a single-agent CLI tool |
| LLM-only memory | Token cost, no cold storage |
