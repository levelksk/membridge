"""memory-capacity-check.py — 记忆容量监测（Linux 版）
检查 memory.json 实体数量和大小，评估注入风险。
"""
import json, os

MEMORY_FILE = os.path.expanduser("~/.hermes/memory/memory.json")

if not os.path.isfile(MEMORY_FILE):
    print("🔴 memory.json 不存在")
    exit(1)

with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

entities = data.get("entities", [])
total_approx = 0
for e in entities:
    name = e.get("name", "")
    etype = e.get("entityType", "")
    obs = "; ".join(e.get("observations", []))
    total_approx += len(name) + len(etype) + len(obs)

INJECT_LIMIT = 5000  # 扩容后 5K
pct = total_approx / INJECT_LIMIT * 100
count = len(entities)

if pct > 90:
    print(f"🔴 紧急: 注入约{total_approx}字 ({pct:.0f}%) — {count}实体，auto-maintain可能压缩细节")
    exit(1)
elif pct > 75:
    print(f"🟡 黄灯: 注入约{total_approx}字 ({pct:.0f}%) — {count}实体，接近上限")
    exit(1)
else:
    print(f"🟢 注入约{total_approx}字 ({pct:.0f}%) / {count}实体 — 正常")
