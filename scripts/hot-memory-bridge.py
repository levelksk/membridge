#!/usr/bin/env python3
"""
Hot Memory Bridge — SQLite → MEMORY.md 自动合并

每 30 分钟 cron 运行一次：
1. 从 SQLite 拉取最高 importance 的非对话条目
2. 合并当前 MEMORY.md 内容（去重、排序）
3. 写入 MEMORY.md，控制在 4K 以内（留 1K buffer）

通道关系：
  SQLite(档案馆,无限) → cron合并 → MEMORY.md(精选,5K) → 会话加载(热层)
"""

import sqlite3
import json
import os
import re
import sys

# ── 自动检测平台路径 ──────────────────────────
if sys.platform == 'win32':
    HERMES_HOME = os.path.expanduser("~/AppData/Local/hermes")
else:
    HERMES_HOME = os.path.expanduser("~/.hermes")
DB_PATH = os.path.join(HERMES_HOME, "sqlitemem.db")
MEMORY_PATH = os.path.join(HERMES_HOME, "memories", "memory.md")
MAX_CHARS = 4000  # 留 1K buffer from 5K limit

# ── 从 SQLite 拉事实 ──────────────────────────────
def fetch_facts(db_path: str) -> list[dict]:
    """从 SQLite 拉非对话条目，按 importance 降序"""
    if not os.path.exists(db_path):
        print(f"[WARN] DB not found: {db_path}")
        return []

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("""
            SELECT content, category, importance, created_at
            FROM entries
            WHERE category != 'conversation'
              AND importance >= 3
            ORDER BY importance DESC, id DESC
        """).fetchall()
    finally:
        conn.close()

    return [
        {"content": r[0], "category": r[1], "importance": r[2], "created": r[3]}
        for r in rows
    ]


# ── 解析 MEMORY.md ────────────────────────────────
def parse_memory(path: str) -> list[dict]:
    """把 MEMORY.md 解析成条目列表"""
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    entries = []
    # 按 [xxx] 分割（Hermes 的条目格式）
    # 示例: [Entity:name] content
    for match in re.finditer(r"(\[.*?\])\s*(.+)", text):
        header = match.group(1)
        content = match.group(2).strip()
        entry_text = f"{header} {content}"
        if entry_text.strip():
            entries.append({"text": entry_text, "source": "memory_md"})

    return entries


# ── 去重合并 ──────────────────────────────────────
def consolidate(sqlite_facts: list[dict], md_entries: list[dict]) -> str:
    """合并 SQLite 事实 + MEMORY.md 条目，去重，控制长度"""
    seen = set()
    lines = []

    def normalize(s: str) -> str:
        """提取核心关键词用于去重"""
        s = s.lower().strip()
        # 去掉类别前缀如 [PREF]、🎯[PREF] 等
        s = re.sub(r"^[^a-z\u4e00-\u9fff]*(\[[a-z]+\])?\s*", "", s)
        s = re.sub(r"[^\w\u4e00-\u9fff]", "", s)
        return s[:80]  # 取前 80 个字符比较

    # 第一遍：收集 MEMORY.md 已有内容做去重参考 + 去重
    deduped_md = []
    for e in md_entries:
        key = normalize(e["text"])
        if key not in seen:
            seen.add(key)
            deduped_md.append(e["text"])

    # 第二遍：从去重后的 MEMORY.md 取 → 保留
    for text in deduped_md:
        if text.strip():
            lines.append(text)

    # 第三遍：从 SQLite 取 → 去重后追加
    for fact in sqlite_facts:
        key = normalize(fact["content"])
        if key in seen:
            continue
        seen.add(key)

        icon = {"pref": "🎯", "env": "🖥️", "fact": "📌", "skill": "🔧"}.get(fact["category"], "📌")
        entry = f"{icon}[{fact['category'].upper()}] {fact['content']}"
        lines.append(entry)

    # 第四遍：裁剪到 MAX_CHARS
    result = []
    total = 0
    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if total + line_len > MAX_CHARS:
            break
        result.append(line)
        total += line_len

    return "\n".join(result)


# ── 写入 MEMORY.md ────────────────────────────────
def write_memory(path: str, content: str):
    """写入 MEMORY.md，保留原文件头注释"""
    header = "# DaoMa's Memory Notes\n# Auto-consolidated by hot-memory-bridge\n\n"
    full = header + content + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(full)
    print(f"[OK] Written {len(content)} chars to {path}")


# ── 报告 ──────────────────────────────────────────
def report(sqlite_count: int, md_count: int, final_chars: int):
    print(f"[STATS] SQLite facts read: {sqlite_count}")
    print(f"[STATS] MEMORY.md entries: {md_count}")
    print(f"[STATS] Final size: {final_chars}/{MAX_CHARS + 1000} chars ({final_chars/(MAX_CHARS+1000)*100:.0f}%)")


if __name__ == "__main__":
    facts = fetch_facts(DB_PATH)
    md_entries = parse_memory(MEMORY_PATH)

    merged = consolidate(facts, md_entries)
    write_memory(MEMORY_PATH, merged)

    report(len(facts), len(md_entries), len(merged))
