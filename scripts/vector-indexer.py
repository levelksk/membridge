#!/usr/bin/env python3
"""vector-indexer.py — 向量索引引擎（通用版）
为 SQLite 中未向量化的条目生成嵌入向量并存储。
使用 paraphrase-multilingual-MiniLM-L12-v2 (384维)
自动检测 GPU/CPU，无需配置
"""
import os, sys
os.environ.setdefault('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')

import sqlite3, pickle, time, json
import numpy as np
from sentence_transformers import SentenceTransformer

# ── 自动检测 GPU ─────────────────────────────────
_DEVICE = 'cpu'
try:
    import torch
    if torch.cuda.is_available():
        _DEVICE = 'cuda'
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"  🎮 GPU: {gpu_name} ({vram:.1f}GB VRAM)")
    else:
        print("  💻 GPU 不可用，使用 CPU")
except ImportError:
    print("  ⚠️  torch 未安装，使用 CPU（建议 pip install torch）")
except Exception as e:
    print(f"  ⚠️  GPU 检测失败: {e}，降级到 CPU")

print(f"  ⚙️  设备: {_DEVICE.upper()}")

# ── 检测平台 ──────────────────────────────────────
if sys.platform == 'win32':
    HERMES_HOME = os.path.expanduser("~/AppData/Local/hermes")
else:
    HERMES_HOME = os.path.expanduser("~/.hermes")
DB = os.path.join(HERMES_HOME, "sqlitemem.db")

MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
BATCH_SIZE = 32

# ── HF 镜像自动回退（国内用户）─ ──────────────────
# 如果连接 huggingface.co 失败且用户没设 HF_ENDPOINT，自动切到 hf-mirror.com
if 'HF_ENDPOINT' not in os.environ:
    try:
        import urllib.request
        urllib.request.urlopen('https://huggingface.co', timeout=5)
    except Exception:
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        print("  🌐 HuggingFace 直连超时，使用镜像: hf-mirror.com")
        print("  💡 如需自定义: export HF_ENDPOINT=你的镜像地址")


# ── 函数定义 ──────────────────────────────────────
def get_unindexed(conn, limit=50):
    c = conn.cursor()
    rows = c.execute("""
        SELECT e.id, e.category, e.importance, e.content
        FROM entries e
        LEFT JOIN vectors v ON e.id = v.entry_id
        WHERE v.entry_id IS NULL
        ORDER BY e.importance DESC, e.id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return rows

def store_vectors(conn, entry_ids, embeddings):
    c = conn.cursor()
    stored = 0
    for eid, emb in zip(entry_ids, embeddings):
        blob = pickle.dumps(emb.astype(np.float32))
        c.execute('INSERT OR IGNORE INTO vectors(entry_id, embedding) VALUES(?,?)', (eid, blob))
        stored += c.rowcount
    conn.commit()
    return stored

def search_similar(conn, query_emb, top_k=5):
    c = conn.cursor()
    rows = c.execute("""
        SELECT v.entry_id, v.embedding, e.category, e.importance, substr(e.content,1,120)
        FROM vectors v
        JOIN entries e ON v.entry_id = e.id
    """).fetchall()

    results = []
    for eid, blob, cat, imp, snippet in rows:
        emb = pickle.loads(blob)
        sim = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
        results.append((sim, eid, cat, imp, snippet))

    results.sort(key=lambda x: -x[0])
    return results[:top_k]


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "index"

    if mode == "index":
        print(f"🔌 加载模型 {MODEL_NAME}...")
        model = SentenceTransformer(MODEL_NAME, device=_DEVICE)
        conn = sqlite3.connect(DB)

        rows = get_unindexed(conn)
        if not rows:
            print("✅ 无未索引条目")
            sys.exit(0)

        # 表结构校验
        schema_ok = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('entries','vectors')").fetchone()[0]
        if schema_ok != 2:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            print(f"  ⚠️ 表结构不完整: {tables}")
            print(f"  期望: entries, vectors | 实际: {tables}")
            sys.exit(1)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(entries)").fetchall()]
        print(f"  📋 entries 表字段: {cols}")

        print(f"📦 待索引: {len(rows)} 条")
        texts = [f"[{r[1]}] {r[3]}" for r in rows]
        entry_ids = [r[0] for r in rows]

        embeddings = model.encode(texts, show_progress_bar=True, batch_size=BATCH_SIZE)
        stored = store_vectors(conn, entry_ids, embeddings)

        total = conn.cursor().execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
        print(f"✅ 已存储 {stored} 条新向量 (总计 {total})")
        conn.close()

    elif mode == "search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "测试"
        model = SentenceTransformer(MODEL_NAME, device=_DEVICE)
        conn = sqlite3.connect(DB)
        query_emb = model.encode([query])[0]
        results = search_similar(conn, query_emb)

        print(f"🔍 向量搜索 '{query}':\n")
        for sim, eid, cat, imp, snippet in results:
            bar = "█" * int(sim * 20)
            print(f'  [{cat:12s}] ⭐{imp} 相似度{sim:.3f} {bar}')
            print(f'    #{eid} {snippet}')
            print()
        conn.close()

    elif mode == "stats":
        conn = sqlite3.connect(DB)
        total = conn.cursor().execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
        total_entries = conn.cursor().execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        total_db = conn.cursor().execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        print(f'vectors: {total}/{total_entries} ({total/max(total_entries,1)*100:.0f}%)')
        conn.close()
