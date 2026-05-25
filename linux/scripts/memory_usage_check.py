"""Check memory usage and report. Returns JSON for cron consumption."""
import json
from pathlib import Path

HERMES_HOME = Path(r"C:\Users\成杰\AppData\Local\hermes")
MEMORY_DIR = HERMES_HOME / "memories"
CONFIG = HERMES_HOME / "config.yaml"

# Parse limits from config
memory_limit = 5000
user_limit = 3000
with open(CONFIG, encoding="utf-8") as f:
    for line in f:
        if "memory_char_limit:" in line:
            try:
                memory_limit = int(line.split(":")[1].strip())
            except: pass
        elif "user_char_limit:" in line:
            try:
                user_limit = int(line.split(":")[1].strip())
            except: pass

# Read files
mem_path = MEMORY_DIR / "MEMORY.md"
user_path = MEMORY_DIR / "USER.md"

mem_chars = mem_path.read_text(encoding="utf-8").strip().__len__() if mem_path.exists() else 0
user_chars = user_path.read_text(encoding="utf-8").strip().__len__() if user_path.exists() else 0

mem_pct = (mem_chars / memory_limit * 100) if memory_limit > 0 else 0
user_pct = (user_chars / user_limit * 100) if user_limit > 0 else 0

result = {
    "memory": {"chars": mem_chars, "limit": memory_limit, "pct": round(mem_pct, 1), "needs_cleanup": mem_pct > 80},
    "user": {"chars": user_chars, "limit": user_limit, "pct": round(user_pct, 1), "needs_cleanup": user_pct > 80},
    "overall_ok": mem_pct <= 80 and user_pct <= 80,
}

# Only print if action needed (silent = clean)
if not result["overall_ok"]:
    print(json.dumps(result, ensure_ascii=False, indent=2))
else:
    # Empty output = silent (cron no_agent pattern)
    pass
