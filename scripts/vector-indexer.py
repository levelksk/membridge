     1|#!/usr/bin/env python3
     2|"""vector-indexer.py — 向量索引引擎（通用版）
     3|为 SQLite 中未向量化的条目生成嵌入向量并存储。
     4|使用 paraphrase-multilingual-MiniLM-L12-v2 (384维)
     5|自动检测 GPU/CPU，无需配置
     6|"""
     7|import os, sys
     8|os.environ.setdefault('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
     9|os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
    10|
    11|import sqlite3, pickle, time, json
    12|import numpy as np
    13|from sentence_transformers import SentenceTransformer
    14|
    15|# ── 自动检测 GPU ─────────────────────────────────
    16|_DEVICE = 'cpu'
    17|try:
    18|    import torch
    19|    if torch.cuda.is_available():
    20|        _DEVICE = 'cuda'
    21|        gpu_name = torch.cuda.get_device_name(0)
    22|        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    23|        print(f"  🎮 GPU: {gpu_name} ({vram:.1f}GB VRAM)")
    24|    else:
    25|        print("  💻 GPU 不可用，使用 CPU")
    26|except ImportError:
    27|    print("  ⚠️  torch 未安装，使用 CPU（建议 pip install torch）")
    28|except Exception as e:
    29|    print(f"  ⚠️  GPU 检测失败: {e}，降级到 CPU")
    30|
    31|print(f"  ⚙️  设备: {_DEVICE.upper()}")
    32|
    33|# ── 检测平台 ├─────────────────────────────────────
    34|if sys.platform == 'win32':
    35|    HERMES_HOME = os.path.expanduser("~/AppData/Local/hermes")
    36|else:
    37|    HERMES_HOME = os.path.expanduser("~/.hermes")
    38|DB = os.path.join(HERMES_HOME, "sqlitemem.db")
    39|
    40|MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
    41|BATCH_SIZE = 32
    42|
    43|def get_unindexed(conn, limit=50):
    44|    c = conn.cursor()
    45|    rows = c.execute("""
    46|        SELECT e.id, e.category, e.importance, e.content
    47|        FROM entries e
    48|        LEFT JOIN vectors v ON e.id = v.entry_id
    49|        WHERE v.entry_id IS NULL
    50|        ORDER BY e.importance DESC, e.id DESC
    51|        LIMIT ?
    52|    """, (limit,)).fetchall()
    53|    return rows
    54|
    55|def store_vectors(conn, entry_ids, embeddings):
    56|    c = conn.cursor()
    57|    stored = 0
    58|    for eid, emb in zip(entry_ids, embeddings):
    59|        blob = pickle.dumps(emb.astype(np.float32))
    60|        c.execute('INSERT OR IGNORE INTO vectors(entry_id, embedding) VALUES(?,?)', (eid, blob))
    61|        stored += c.rowcount
    62|    conn.commit()
    63|    return stored
    64|
    65|def search_similar(conn, query_emb, top_k=5):
    66|    c = conn.cursor()
    67|    rows = c.execute("""
    68|        SELECT v.entry_id, v.embedding, e.category, e.importance, substr(e.content,1,120)
    69|        FROM vectors v
    70|        JOIN entries e ON v.entry_id = e.id
    71|    """).fetchall()
    72|
    73|    results = []
    74|    for eid, blob, cat, imp, snippet in rows:
    75|        emb = pickle.loads(blob)
    76|        sim = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
    77|        results.append((sim, eid, cat, imp, snippet))
    78|
    79|    results.sort(key=lambda x: -x[0])
    80|    return results[:top_k]
    81|
    82|if __name__ == "__main__":
    83|    mode = sys.argv[1] if len(sys.argv) > 1 else "index"
    84|
    85|    if mode == "index":
    86|        print(f"🔌 加载模型 {MODEL_NAME}...")
    87|        model = SentenceTransformer(MODEL_NAME, device=_DEVICE)
    88|        conn = sqlite3.connect(DB)
    89|
    90|        rows = get_unindexed(conn)
    91|        if not rows:
    92|            print("✅ 无未索引条目")
    93|            sys.exit(0)
    94|
    95|        # 表结构校验：确认 entries 和 vectors 表存在且有期望字段
        schema_ok = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('entries','vectors')").fetchone()[0]
        if schema_ok != 2:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            print(f"  ⚠️ 表结构不完整: {tables}")
            print(f"  期望: entries, vectors | 实际: {tables}")
            sys.exit(1)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(entries)").fetchall()]
        print(f"  📋 entries 表字段: {cols}")
        print(f"📦 待索引: {len(rows)} 条")
    96|        texts = [f"[{r[1]}] {r[3]}" for r in rows]
    97|        entry_ids = [r[0] for r in rows]
    98|
    99|        embeddings = model.encode(texts, show_progress_bar=True, batch_size=BATCH_SIZE)
   100|        stored = store_vectors(conn, entry_ids, embeddings)
   101|
   102|        total = conn.cursor().execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
   103|        print(f"✅ 已存储 {stored} 条新向量 (总计 {total})")
   104|        conn.close()
   105|
   106|    elif mode == "search":
   107|        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "测试"
   108|        model = SentenceTransformer(MODEL_NAME, device=_DEVICE)
   109|        conn = sqlite3.connect(DB)
   110|        query_emb = model.encode([query])[0]
   111|        results = search_similar(conn, query_emb)
   112|
   113|        print(f"🔍 向量搜索 '{query}':\n")
   114|        for sim, eid, cat, imp, snippet in results:
   115|            bar = "█" * int(sim * 20)
   116|            print(f'  [{cat:12s}] ⭐{imp} 相似度{sim:.3f} {bar}')
   117|            print(f'    #{eid} {snippet}')
   118|            print()
   119|        conn.close()
   120|
   121|    elif mode == "stats":
   122|        conn = sqlite3.connect(DB)
   123|        total = conn.cursor().execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
   124|        total_entries = conn.cursor().execute("SELECT COUNT(*) FROM entries").fetchone()[0]
   125|        print(f'vectors: {total}/{total_entries} ({total/max(total_entries,1)*100:.0f}%)')
   126|        conn.close()
   127|