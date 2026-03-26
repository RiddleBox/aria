# ARIA 后续发展规划

> 版本：v1.3 · 2026-03-26
> 基于第一性原理 · 奥卡姆剃刀 · 实际使用场景确认

---

## 核心原则（不变）

- **意图优先**：ARIA 永远是"听懂你说什么，再决定做什么"，不是功能堆砌
- **不造轮子**：每个能力找最成熟的现有方案接入，ARIA 只做胶水层
- **模块热插拔**：需要什么功能时，一个新文件加进来，核心不动
- **接口先行**：Godot 形象层的接口现在就留好，到时直接对接

---

## Phase 1.5 · 收尾（当前）

**目标：让 Phase 1 真正可用**

- [x] 集成测试完成（语音 → 视觉处理 → AI响应 端到端跑通）✅ 2026-03-25
- [x] 视觉优化完成（JPEG压缩 + 1080p降采样，token节省约80%）✅ 2026-03-25
- [ ] 游戏场景热键测试（`Ctrl+\`` 是否被游戏拦截）← **下一步**
- [ ] 确认 `core/bus.py` 事件格式，为 Godot 对接做准备

---

## Phase 2 · 游戏录屏

**目标：说"帮我记刚才那段" → 保存过去 N 秒游戏画面**

- Replay Buffer 代码已完成（`modules/actions/replay_buffer.py`）
- 待本地验证 d3dshot 能否捕获游戏全屏
- 时间窗口：**15 秒**（游戏场景够用，文件不会太大）
- 顺带实现 `convert` 模块（视频 → GIF，ffmpeg 一条命令）
- 文档/工作场景：直接截屏，不需要回溯

---

## Phase 3 · 模块扩展框架

**目标：建立"30 分钟接入任何新能力"的标准**

每个模块只需满足接口：
```python
MANIFEST = { "name": "xxx", "triggers": [...], "description": "..." }
def run(context: dict, config: dict) -> dict: ...
```
放进 `modules/actions/` 自动被 Dispatcher 加载，零侵入核心。

**候选模块（按需接入，不提前实现）：**

| 模块 | 接入方案 | 触发词示例 |
|---|---|---|
| `browse` | `playwright` 或 `requests+readability` | "帮我查一下 XX" |
| `remind` | `schedule` 库 + Windows 通知 | "提醒我 XX 点做 XX" |
| `search` | 本地 `ripgrep` 搜 vault | "找一下我之前记的 XX" |
| `read` | `pymupdf` 读 PDF / `readability` 读网页 | "读一下这篇" |

---

## Phase 4 · Godot 对接接口

**ARIA 只发事件，不关心 Godot 怎么渲染**

`core/bus.py` 每次动作完成后广播：
```python
{
  "event": "aria.action_complete",
  "action": "archive",        # 做了什么
  "reply": "记好了",           # 语音回复内容
  "timestamp": "...",
  "data": { ... }             # 可选：截图路径、归档路径等
}
```
Godot 通过 WebSocket 或本地 socket 监听，驱动角色表情/文字反馈。
Godot 形象模块由用户主导设计，ARIA 只负责留好接口。

---

## Phase 5 · 远期（按需）

ARIA 本质是意图路由器 + 工具集。未来能力扩展方向：
- 技能市场化：模块可从外部加载，类似插件系统
- 唤醒词：常驻监听，手不在键盘时触发
- 本地轻量视觉感知：主动检测屏幕变化（Phase 2 被动→主动）
- 硬件接入：智能眼镜等外部感知设备

---

## 执行节奏

```
现在        → Phase 1.5 收尾（热键测试 + 接口确认）
本地验证后  → Phase 2（录屏接入主流程）
用一段时间  → 看实际缺什么模块，按需接入 Phase 3
Godot 启动时 → Phase 4 接口对齐（用户主导，ARIA 配合）
```

---

## 决策记录

| 决策 | 结论 |
|---|---|
| 录屏回溯时长 | 15 秒（游戏场景），文档场景不需要回溯直接截屏 |
| 模块扩展方式 | 热插拔，放入 `modules/actions/` 自动加载 |
| Godot 对接 | ARIA 发事件，Godot 监听渲染，完全解耦 |
| 形象模块 | 用户用 Claude Game Studio 自行设计，ARIA 不参与 |
| 能力扩展哲学 | 需要时接入成熟方案，不提前实现，不造轮子 |
