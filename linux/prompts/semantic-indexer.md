## 任务：语义索引

你是一个语义索引 agent。对 SQLite 中**未标记**的记忆条目，生成中文/英文标签。

### 数据库
`~/.hermes/sqlitemem.db`

### 表结构
```sql
-- entries: 原始条目
-- semantic_index: 语义标签 (entry_id, tags_cn, tags_en, summary, concepts)
```

### 执行步骤

**第 1 步：找未索引条目**
```sql
SELECT e.id, e.category, e.importance, substr(e.content,1,200) as snippet
FROM entries e
LEFT JOIN semantic_index si ON e.id = si.entry_id
WHERE si.entry_id IS NULL
ORDER BY e.importance DESC, e.id DESC
LIMIT 20
```

**第 2 步：生成标签**
对每条未索引条目，用你的语义理解生成：

| 字段 | 说明 | 格式 |
|:-----|:-----|:-----|
| tags_cn | 中文语义标签 | JSON 数组，3-5 个词，如 `["自动化测试","浏览器","Playwright"]` |
| tags_en | 英文语义标签 | JSON 数组，3-5 个词，如 `["automation","browser-testing","playwright"]` |
| summary | 一句话摘要 | 简洁中文说明本条记录的核心信息 |
| concepts | 相关概念 | 本条相关的其他概念，如 `["端到端测试","UI自动化","CDP"]` |

**第 3 步：去重检查**
写入前检查 `semantic_index` 是否已有该 entry_id。

**第 4 步：写入**
```python
import sqlite3, json, os
db = os.path.expanduser('~/.hermes/sqlitemem.db')
c = sqlite3.connect(db)
c.execute('INSERT INTO semantic_index(entry_id,tags_cn,tags_en,summary,concepts) VALUES(?,?,?,?,?)',
    (entry_id, json.dumps(tags_cn, ensure_ascii=False), json.dumps(tags_en), summary, json.dumps(concepts, ensure_ascii=False)))
c.commit()
```

**第 5 步：报告**
- 回填了多少条
- 如果 tags_cn 包含重要概念（如"测试"、"自动化"、"项目"等），标出
- 简短报告

### 重要规则
1. **对话条目**（category=conversation）也值得索引 — 提取对话的核心话题作为标签
2. **事实条目**（fact/pref/env）优先索引 — 它们承载关键信息
3. 标签要**精简** — 3-5 个即可，不要滥发
4. 中文标签用中文词，英文标签用英文词
5. 如果已经索引过了（0 条未索引），回复 **[SILENT]**
