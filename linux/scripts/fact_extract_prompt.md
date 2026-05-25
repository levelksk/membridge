# Fact Extraction — Cron 任务 Prompt

> 供 `memory-extract` cron job 使用，每 30 分钟触发 agent 自我思考提取事实。

## 设计原则

- **不调用外部 LLM** — agent 自己的推理即 LLM，零额外成本
- **静默执行** — 默认 `[SILENT]`，仅重要性 5 才在对话中报告
- **双通道互补** — 对话中的 real-time 提取 + cron 定时兜底
- **增量提取** — 只处理上次提取后的新对话，不重复扫描

## 触发时机

| 条件 | 行为 |
|:----|:----|
| cron 每 30 分钟 | 检查最近 30 分钟的高频/重要对话 |
| 对话中（real-time） | 遇到明显事实时立即提取 |
| 两者同时触发 | 去重合并，cron 跳过已提取部分 |

## Prompt 模板

> 以下 prompt 由 cron job 注入 Agent 的系统提示中：

```
【事实提取任务】

你需要在 1-2 轮思考内完成，不要过度分析。

### 本轮任务

1. 用 `memory_search` 查询过去 30 分钟的新对话（target='auto', limit=20）
2. 阅读这些对话，提取其中值得记录的事实
3. 已有事实不要重复写

### 事实分类

每条提取结果需要标一个类别：

| 类别 | 含义 | 示例 |
|:----|:----|:----|
| `pref` | 用户偏好、习惯 | 用户喜欢简洁回答，偏好英文界面 |
| `env` | 环境信息 | 用户用 Windows 11，项目路径 D:/projects/ |
| `fact` | 客观事实 | 用户生日 5 月 20 日，公司 50 人规模 |
| `skill` | 用户具备的技能/知识 | 用户精通 Python 和 SQL，会 Docker |

### 输出格式

```
[EXTRACT] category | importance(1-5) | fact_text

[SILENT]   ← 如果 importance < 5
[REPORT]   ← 如果 importance == 5（罕见，需用户确认）
```

### 等级定义

| 等级 | 含义 | 输出 |
|:----|:----|:----:|
| 5 | 关键事实（密码、地址、生死攸关） | `[REPORT]` 告知用户 |
| 3-4 | 有用事实（工作偏好、项目细节） | `[SILENT]` 静默写入 |
| 1-2 | 临时信息（一次性话题） | 跳过，不值得记 |

### 执行规则

1. **静默原则** — 99% 的情况用 `[SILENT]`，用户不应感知 cron 在运行
2. **重要性 5** 才 `[REPORT]` — 仅在发现密码、紧急地址等关键信息时打断用户
3. **不要超时** — 1-2 轮思考内完成，避免拖长推理
4. **已有不重复** — 检查 MEMORY.md 里已有的事实，避免重复
5. **合并同类** — 如果多条对话指向同一事实，合成一条精炼描述
```

## 执行流程

```
┌──────────────────────┐
│  Cron 每 30 分钟触发   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  注入 [[SILENT]] prompt │  ← 不打断当前对话
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Agent 思考 1-2 轮      │  ← 零额外 LLM 成本
│  ├─ memory_search     │
│  └─ 分类 + 写入 MEMORY │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  输出结果              │
│  ├─ [SILENT] → 静默    │  ← 默认路径
│  └─ [REPORT] → 通知用户 │  ← 仅 importance=5
└──────────────────────┘
```

## 与 real-time 提取的关系

| 通道 | 触发 | 优势 | 劣势 |
|:----|:----|:----|:----|
| Real-time | 对话中自然发生 | 上下文完整，提取准确 | 可能遗漏忙碌时的信息 |
| Cron 提取 | 每 30 分钟 | 兜底，覆盖遗忘 | 上下文可能已不在窗口 |
| 互补结果 | 两者合并 | 双重保障，去重后写入 | 需注意重复写入 |

## 注册命令

```bash
# 添加 cron 任务
hermes cron add --name memory-extract --schedule "every 30min" \
  --prompt-file scripts/fact_extract_prompt.md \
  "Extract facts from recent conversation silently"

# 查看 cron 状态
hermes cron list | grep memory-extract

# 手动触发
hermes cron run memory-extract

# 删除
hermes cron remove memory-extract
```
