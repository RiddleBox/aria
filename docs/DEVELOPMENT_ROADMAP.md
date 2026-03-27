# ARIA 后续发展规划

> 版本：v1.4 · 2026-03-27
> 基于第一性原理 · 奥卡姆剃刀 · 实际使用场景确认

---

## 核心原则（不变）

- **意图优先**：ARIA 永远是"听懂你说什么，再决定做什么"，不是功能堆砌
- **不造轮子**：每个能力找最成熟的现有方案接入，ARIA 只做胶水层
- **模块热插拔**：需要什么功能时，一个新文件加进来，核心不动
- **接口先行**：Godot 形象层的接口现在就留好，到时直接对接
- **记忆/表现分离**：ARIA 存事实，Godot 用性格决定怎么表现

---

## Phase 1.5 · 收尾 ✅

- [x] 集成测试完成（语音 → 视觉处理 → AI响应 端到端跑通）✅ 2026-03-25
- [x] 视觉优化完成（JPEG压缩 + 1080p降采样，token节省约80%）✅ 2026-03-25
- [x] 视觉模型切换（Gemini 配额耗尽 → GLM-4V-Flash）✅ 2026-03-26
- [x] 语音播放修复（优先用 winmm MCI，兼容 Python 3.14）✅ 2026-03-26
- [x] capture action 上线（意图识别 + 截图 + 动态录制时长）✅ 2026-03-26
- [x] bus.py 事件格式确认，Godot 对接接口就绪 ✅ 2026-03-27
- [ ] 录屏视频合成（ffmpeg 调用失败，frames 截到了但合成报错）← 暂搁置

---

## Phase 2 · 游戏录屏 ⏸ 暂搁置

录屏（replay_buffer）存在兼容性问题，暂不推进。
等有实际需求或找到更稳定方案再回来。

---

## Phase 3 · 桌宠核心功能 ← 当前重点

**目标：让 ARIA 真正像一个陪伴玩家的桌宠**

### 3.1 能力发现 ✅ 2026-03-27
- [x] `core/skill_finder.py`：找不到模块时搜 PyPI 推荐，零 token 消耗
- [x] `core/dispatcher.py`：fallback 改为调 skill_finder，返回推荐而非报错

### 3.2 窗口感知 ✅ 2026-03-27
- [x] `core/window_context.py`：获取前台窗口/进程，识别游戏场景
- [x] `core/perception.py`：每次指令自动注入 window_context
- [x] 内置 30+ 款游戏进程名映射，窗口标题关键词兜底
- [x] 依赖：`pip install pywin32 psutil`

### 3.3 快速记录 ✅ 2026-03-27
- [x] `modules/actions/quick_note.py`：语音一句话 → 追加写入今日笔记
- [x] 游戏中记录自动打 `🎮[游戏名]` 标签，工作场景打 `💼[窗口名]`

### 3.4 游戏截图标签 ✅ 2026-03-27
- [x] `modules/actions/capture.py`：截图归档自动带游戏名标签
- [x] Obsidian tags 自动加 `game/游戏名` + `gaming`

### 3.5 记忆系统 ✅ 2026-03-27
- [x] `core/memory.py`：四层记忆结构，全局单例
- [x] `main.py`：每次交互后写 memory，重要动作写 events

**记忆四层结构：**
```
interactions[]  近期对话流水（50条滚动，意图解析上下文用）
facts{}         用户偏好/信息（用户自己说的）
events[]        重要事件精华（截图/记录/提醒，Godot 读这里）
summary         自动压缩摘要（每20条触发）
```

**Godot 读取接口：**
```python
memory.get_recent_events(n)   # 最近发生了什么
memory.get_facts()             # 用户是谁、有什么偏好
memory.get_summary()           # 最近在干什么（摘要）
```

### 3.6 待实现

| 功能 | 说明 | 优先级 |
|---|---|---|
| `remind` 模块 | 语音设提醒，Windows 气泡通知 | 高 |
| `search` 模块 | 搜 Obsidian vault 历史记录 | 中 |
| `browse` 模块 | 帮查网页/攻略 | 中 |
| facts 自动提取 | 对话中自动识别用户信息存入 facts | 中 |
| memory HTTP API | 暴露给 Godot 的读取接口 | Phase 4 时做 |

---

## Phase 4 · Godot 对接接口

**ARIA 只发事件 + 提供记忆读取，不关心 Godot 怎么渲染**

### 事件总线（已就绪）
`core/bus.py` 每次动作完成后广播，Godot 通过 WebSocket 订阅：
```python
aria.action_complete  → {"action": str, "reply": str, "data": {...}}
aria.state_change     → {"state": "idle|listening|thinking|speaking|working"}
aria.speaking         → {"text": str}
aria.skill_not_found  → {"action": str, "suggestions": [...]}
```

### 记忆读取（Phase 4 时暴露 HTTP/WebSocket 接口）
```python
# Godot 拿这些数据，用角色性格决定怎么表现
memory.get_recent_events(n)   # 最近发生了什么
memory.get_facts()             # 用户偏好
memory.get_summary()           # 近期摘要
```

**职责分工：**
- ARIA：存事实（发生了什么、用户说了什么、用户喜欢什么）
- Godot：表现层（用什么语气、什么表情、什么时候主动说话）

---

## Phase 5 · 远期（按需）

- 唤醒词：常驻监听，手不在键盘时触发
- 本地轻量视觉感知：主动检测屏幕变化
- 技能市场化：模块从外部加载，类似插件系统
- 硬件接入：智能眼镜等外部感知设备

---

## 决策记录

| 决策 | 结论 |
|---|---|
| 录屏回溯 | 暂搁置，兼容性问题未解决 |
| 模块扩展方式 | 热插拔，放入 `modules/actions/` 自动加载 |
| Godot 对接 | ARIA 发事件 + 提供记忆接口，Godot 监听渲染，完全解耦 |
| 记忆/性格分离 | ARIA 存事实，Godot 用性格决定表现方式 |
| 能力发现 | 找不到模块时推荐 PyPI 资源，用户手动安装，零 token 消耗 |
| 形象模块 | Godot 项目那边负责，ARIA 留好接口 |
| 能力扩展哲学 | 需要时接入成熟方案，不提前实现，不造轮子 |
