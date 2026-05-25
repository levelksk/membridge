"""memory-capacity-check.py — 记忆容量监测
检查 memory.json 实体数量和大小，评估注入风险。
memory.json 是持久存储（不限大小），
注入的是格式化后的 ~2200 字子集。
"""
import json, os

if sys.platform == 'win32':
    MEMORY_FILE = os.path.expanduser("~/AppData/Local/hermes/memory/memory.json")
else:
    MEMORY_FILE = os.path.expanduser("~/.hermes/memory/memory.json")

if not os.path.isfile(MEMORY_FILE):
    print("🔴 memory.json 不存在")
    exit(1)

with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

entities = data.get("entities", [])
# 近似计算注入占用：name + type + observations
total_approx = 0
for e in entities:
    name = e.get("name", "")
    etype = e.get("entityType", "")
    obs = "; ".join(e.get("observations", []))
    total_approx += len(name) + len(etype) + len(obs)

INJECT_LIMIT = 2200
pct = total_approx / INJECT_LIMIT * 100
count = len(entities)

# 输出
if pct > 90:
    print(f"🔴 紧急: 注入约{total_approx}字 ({pct:.0f}%) — {count}实体，auto-maintain可能压缩细节")
    exit(1)
elif pct > 75:
    print(f"🟡 黄灯: 注入约{total_approx}字 ({pct:.0f}%) — {count}实体，接近上限")
    exit(1)
else:
    print(f"🟢 注入约{total_approx}字 ({pct:.0f}%) / {count}实体 — 正常")
