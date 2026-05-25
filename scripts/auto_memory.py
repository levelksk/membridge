"""auto_memory.py — 自动记忆管理引擎 (v1.0)
基于 ai-test-platform 的 local-memory v4 设计

我（Agent）在用Hermes时自动调用此模块，实现：
- 自动检测值得记的信息 → 写入结构化的 JSON 存储
- 自动搜索/召回 → 帮我找回之前的知识
- 自动维护 → 去重/合并/过期/备份

用法示例（从 execute_code 中调用）：
  from hermes_tools import terminal
  terminal('python3 ~/path/auto_memory.py save 用户 偏好 简洁回答 permanent')
  terminal('python3 ~/path/auto_memory.py search 代理')
  terminal('python3 ~/path/auto_memory.py maintain')
"""
import json, os, time, shutil, re, sys, argparse
from datetime import datetime, timezone
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────
if sys.platform == 'win32':
    DEFAULT_HERMES_HOME = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes")
else:
    DEFAULT_HERMES_HOME = os.path.expanduser("~/.hermes")
HERMES_HOME = Path(os.environ.get("HERMES_HOME", DEFAULT_HERMES_HOME))
MEMORY_DIR = HERMES_HOME / "memory"
MEMORY_FILE = MEMORY_DIR / "memory.json"
BACKUP_DIR = MEMORY_DIR / "backups"
INDEX_FILE = MEMORY_DIR / "memory-index.json"
SUMMARY_FILE = MEMORY_DIR / "session-summary.md"
MAX_BACKUPS = 15
CURRENT_VERSION = "1.0.0"

# TTL 配置（秒）
TTL = {
    "permanent": None,       # 永不过期
    "longTerm": 7776000,     # 90 天
    "shortTerm": 1209600,    # 14 天
}

# ── 数据结构 ─────────────────────────────────────
DEFAULT_MEMORY = {
    "version": CURRENT_VERSION,
    "lastUpdated": "",
    "entities": [],
    "relations": [],
}

# ── 文件操作 ─────────────────────────────────────
def _ensure_dir():
    """确保目录存在"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def _load() -> dict:
    """加载 memory.json，损坏自动恢复"""
    _ensure_dir()
    if not MEMORY_FILE.exists():
        return dict(DEFAULT_MEMORY)
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        # 从备份恢复
        backups = sorted(BACKUP_DIR.glob("memory-*.json.bak"))
        if backups:
            shutil.copy(backups[-1], MEMORY_FILE)
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return dict(DEFAULT_MEMORY)

def _save(data: dict):
    """原子写入：先写 tmp 后 rename"""
    _ensure_dir()
    tmp = MEMORY_FILE.with_suffix(".tmp")
    data["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(MEMORY_FILE)

# ── 实体 CRUD ────────────────────────────────────
def save_entity(name: str, entity_type: str, observations: list,
                memory_type: str = "longTerm", ttl_days: int = None,
                auto_merge: bool = True) -> dict:
    """保存/更新一个实体
    
    Args:
        name: 实体名称
        entity_type: 类型（UserPreference/Env/Project/Tool/Fix/Workflow）
        observations: 观察列表
        memory_type: permanent/longTerm/shortTerm
        ttl_days: 自定义过期天数
        auto_merge: 同实体自动合并
    Returns:
        写入后的实体
    """
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    
    if ttl_days:
        ttl = ttl_days * 86400
    else:
        ttl = TTL.get(memory_type, 7776000)
    
    # 查找已有实体
    existing = None
    for e in data["entities"]:
        if e["name"] == name:
            existing = e
            break
    
    if existing and auto_merge:
        # 合并观察（去重）
        existing_obs = set(existing.get("observations", []))
        for obs in observations:
            existing_obs.add(obs)
        existing["observations"] = list(existing_obs)
        existing["entityType"] = entity_type
        existing["memoryType"] = memory_type
        existing["lastUpdated"] = now
        existing["lastAccessedAt"] = now
        existing["accessCount"] = existing.get("accessCount", 0) + 1
        if ttl:
            existing["ttl"] = ttl
        result = existing
    else:
        # 新建
        entity = {
            "name": name,
            "entityType": entity_type,
            "observations": list(observations),
            "memoryType": memory_type,
            "createdAt": now,
            "lastUpdated": now,
            "lastAccessedAt": now,
            "accessCount": 1,
        }
        if ttl:
            entity["ttl"] = ttl
        data["entities"].append(entity)
        result = entity
    
    _save(data)
    return result

def get_entity(name: str) -> dict:
    """获取实体，同时更新访问计数"""
    data = _load()
    for e in data["entities"]:
        if e["name"] == name:
            e["accessCount"] = e.get("accessCount", 0) + 1
            e["lastAccessedAt"] = datetime.now(timezone.utc).isoformat()
            _save(data)
            return e
    return None

def delete_entity(name: str) -> bool:
    """删除实体"""
    data = _load()
    before = len(data["entities"])
    data["entities"] = [e for e in data["entities"] if e["name"] != name]
    if len(data["entities"]) < before:
        _save(data)
        return True
    return False

# ── 搜索 ─────────────────────────────────────────
def search_entities(query: str, limit: int = 10) -> list:
    """搜索实体（名称+观察全文匹配）"""
    data = _load()
    query_lower = query.lower()
    results = []
    
    for e in data["entities"]:
        score = 0
        # 名称匹配加分
        if query_lower in e["name"].lower():
            score += 10
        # 观察匹配
        for obs in e.get("observations", []):
            if query_lower in obs.lower():
                score += 5
        # 类型匹配
        if query_lower in e.get("entityType", "").lower():
            score += 3
        
        if score > 0:
            results.append((score, e))
    
    results.sort(key=lambda x: -x[0])
    return [r[1] for r in results[:limit]]

def get_all_entities(memory_type: str = None) -> list:
    """获取所有实体，可选按类型过滤"""
    data = _load()
    if memory_type:
        return [e for e in data["entities"] if e.get("memoryType") == memory_type]
    return data["entities"]

# ── 维护 ─────────────────────────────────────────
def _is_expired(entity: dict) -> bool:
    """判断实体是否过期"""
    ttl = entity.get("ttl")
    if ttl is None:
        return False  # permanent
    updated = entity.get("lastUpdated", entity.get("createdAt", ""))
    if not updated:
        return False
    try:
        updated_dt = datetime.fromisoformat(updated)
        age = (datetime.now(timezone.utc) - updated_dt).total_seconds()
        return age > ttl
    except:
        return False

def dedup_observations() -> int:
    """去重：同一实体内去除重复观察"""
    data = _load()
    removed = 0
    for e in data["entities"]:
        obs = e.get("observations", [])
        unique = list(dict.fromkeys(obs))  # 保持顺序去重
        removed += len(obs) - len(unique)
        e["observations"] = unique
    _save(data)
    return removed

def merge_similar() -> int:
    """合并相似实体（名称相似度 >0.7 的合并）"""
    data = _load()
    entities = data["entities"]
    merged = 0
    
    def similarity(a: str, b: str) -> float:
        a_set = set(a.lower())
        b_set = set(b.lower())
        if not a_set or not b_set:
            return 0
        return len(a_set & b_set) / max(len(a_set | b_set), 1)
    
    i = 0
    while i < len(entities):
        j = i + 1
        while j < len(entities):
            if similarity(entities[i]["name"], entities[j]["name"]) > 0.7:
                # 合并观察
                all_obs = list(dict.fromkeys(
                    entities[i].get("observations", []) + 
                    entities[j].get("observations", [])
                ))
                entities[i]["observations"] = all_obs
                entities[i]["accessCount"] = max(
                    entities[i].get("accessCount", 0),
                    entities[j].get("accessCount", 0)
                )
                entities.pop(j)
                merged += 1
            else:
                j += 1
        i += 1
    
    if merged > 0:
        _save(data)
    return merged

def expire_entities() -> list:
    """清理过期的 shortTerm 实体"""
    data = _load()
    expired = []
    before = len(data["entities"])
    data["entities"] = [e for e in data["entities"] if not _is_expired(e)]
    expired_count = before - len(data["entities"])
    if expired_count > 0:
        _save(data)
    return {"removed": expired_count, "before": before, "after": len(data["entities"])}

def backup() -> str:
    """创建备份"""
    _ensure_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"memory-{timestamp}.json.bak"
    if MEMORY_FILE.exists():
        shutil.copy(MEMORY_FILE, backup_path)
    # 轮转
    backups = sorted(BACKUP_DIR.glob("memory-*.json.bak"))
    while len(backups) > MAX_BACKUPS:
        backups[0].unlink()
        backups.pop(0)
    return str(backup_path)

def maintain() -> dict:
    """全自动维护"""
    report = {}
    report["dedup"] = dedup_observations()
    report["merge"] = merge_similar()
    report["expire"] = expire_entities()
    report["backup"] = backup()
    
    # 统计
    data = _load()
    report["total_entities"] = len(data["entities"])
    report["permanent"] = len([e for e in data["entities"] if e.get("memoryType") == "permanent"])
    report["longTerm"] = len([e for e in data["entities"] if e.get("memoryType") == "longTerm"])
    report["shortTerm"] = len([e for e in data["entities"] if e.get("memoryType") == "shortTerm"])
    
    return report

# ── 构建上下文（给 Hermes 用） ───────────────────
def build_context(limit_entries: int = 15) -> str:
    """构建注入 Hermes 上下文的文本"""
    data = _load()
    entities = data["entities"]
    
    # 按访问次数排序
    entities.sort(key=lambda e: -(e.get("accessCount", 0)))
    
    lines = []
    for e in entities[:limit_entries]:
        lines.append(f"[Entity:{e['name']}]")
        lines.append(f"  类型: {e.get('entityType', 'Unknown')}")
        obs = e.get("observations", [])
        if obs:
            lines.append(f"  观察: {obs[:3]}")  # 最多3条
        lines.append(f"  等级: {e.get('memoryType', 'longTerm')}")
        lines.append("")
    
    total = len(entities)
    usage = len(json.dumps({"entities": entities}, ensure_ascii=False))
    lines.append(f"📊 记忆统计: 总计 {total} 实体, {usage/1024:.0f}KB")
    
    return "\n".join(lines)

def build_mini_context() -> str:
    """超紧凑上下文（给Hermes内置记忆用，控制在500字内）"""
    data = _load()
    entities = data["entities"]
    entities.sort(key=lambda e: -(e.get("accessCount", 0)))
    
    lines = ["📦 auto_memory 上下文:"]
    for e in entities[:10]:
        obs = e.get("observations", [])
        obs_text = obs[0] if obs else ""
        if len(obs_text) > 60:
            obs_text = obs_text[:57] + "..."
        lines.append(f"·{e['name']}({e.get('entityType','?')}): {obs_text}")
    
    total = len(entities)
    lines.append(f"📊 {total}实体")
    return "\n".join(lines)

# ── CLI ──────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Auto Memory Engine")
    parser.add_argument("action", choices=["save", "get", "delete", "search",
                                           "list", "maintain", "backup", "context", "mini_context", "stats"])
    parser.add_argument("args", nargs="*", help="action arguments")
    args = parser.parse_args()
    
    if args.action == "save":
        if len(args.args) < 3:
            print('Usage: save <name> <entity_type> <observation> [memory_type]')
            print('  entity_type: UserPreference/Env/Project/Tool/Fix/Workflow')
            print('  memory_type: permanent/longTerm/shortTerm (default: longTerm)')
            return
        name = args.args[0]
        etype = args.args[1]
        obs = args.args[2:]
        mtype = "longTerm"
        if len(args.args) > 3:
            mtype = obs.pop()
        result = save_entity(name, etype, [obs[-1]] if isinstance(obs, list) else [obs], mtype) if len(args.args) == 4 \
            else save_entity(name, etype, obs, mtype)
        print(json.dumps({"saved": name, "type": etype, "observations": len(result.get("observations",[]))}, ensure_ascii=False))
    
    elif args.action == "get":
        if not args.args:
            print("Usage: get <name>")
            return
        e = get_entity(args.args[0])
        if e:
            print(json.dumps(e, ensure_ascii=False, indent=2))
        else:
            print(f"Not found: {args.args[0]}")
    
    elif args.action == "delete":
        if not args.args:
            print("Usage: delete <name>")
            return
        ok = delete_entity(args.args[0])
        print("deleted" if ok else "not found")
    
    elif args.action == "search":
        if not args.args:
            print("Usage: search <query>")
            return
        results = search_entities(args.args[0])
        for e in results:
            print(f"[{e.get('memoryType','?')}] {e['name']} ({e.get('entityType','?')})")
            for obs in e.get("observations", [])[:2]:
                print(f"  → {obs}")
            print()
        print(f"--- {len(results)} result(s) ---")
    
    elif args.action == "list":
        entities = get_all_entities(args.args[0] if args.args else None)
        for e in entities:
            print(f"[{e.get('memoryType','?')}] {e['name']} ({e.get('entityType','?')}) - {len(e.get('observations',[]))} obs")
    
    elif args.action == "maintain":
        report = maintain()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    
    elif args.action == "backup":
        path = backup()
        print(f"Backup saved: {path}")
    
    elif args.action == "context":
        print(build_context())
    
    elif args.action == "mini_context":
        print(build_mini_context())
    
    elif args.action == "stats":
        data = _load()
        entities = data["entities"]
        total = len(entities)
        total_obs = sum(len(e.get("observations", [])) for e in entities)
        by_type = {}
        by_mtype = {}
        for e in entities:
            t = e.get("entityType", "Unknown")
            by_type[t] = by_type.get(t, 0) + 1
            m = e.get("memoryType", "longTerm")
            by_mtype[m] = by_mtype.get(m, 0) + 1
        size = len(json.dumps(data, ensure_ascii=False))
        print(f"Total entities: {total}")
        print(f"Total observations: {total_obs}")
        print(f"Storage: {size/1024:.1f}KB")
        print(f"By type: {json.dumps(by_type)}")
        print(f"By memory type: {json.dumps(by_mtype)}")

if __name__ == "__main__":
    main()
