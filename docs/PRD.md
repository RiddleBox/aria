# ARIA — Product Requirements Document

> 版本：v0.2 · 2026-03-25
> 状态：Phase 1 核心流程已验证，Phase 1.5 收尾中

---

## 一、第一性原理：核心问题是什么

**人与 AI 协作时存在信息损失。**

手动输入、截图、复制粘贴——这些动作都在"我发现有价值的东西"和"AI 处理它"之间制造了摩擦和损耗。结果是：要么懒得记，要么记了但上下文丢了，要么事后找不到。

**ARIA 要解决的根本问题：**

> 让 AI 能"见我所见"，在我电脑使用的任意场景中，以最小摩擦捕捉我想保留的信息和观点。

---

## 二、核心交互模型

### 触发

```
快捷键按下 → 开始说话 → 松开/静音自动识别
```

- 快捷键是高优先级实现方式（游戏场景中键盘/鼠标更可靠）
- 唤醒词作为次级方式（日常工作场景，手不在键盘时）
- 早期也允许打字输入（降低测试门槛）

### 意图优先，感知按需

```
我说的话（指令）
    │
    ▼
AI 理解意图
    │
    ├── 需要视觉上下文？→ 截图 / 触发 Replay Buffer
    ├── 不需要？→ 直接处理
    │
    ▼
执行对应动作（归档 / 回答 / 转换 / ...）
    │
    ├── 语音回应我
    └── 广播事件到 bus（Godot 等外部消费）
```

**关键原则：截图和录屏不是默认行为，而是 AI 根据指令内容判断是否需要的上下文工具。**

### 典型交互示例

| 我说的话 | AI 判断 | 执行动作 |
|---|---|---|
| "帮我记这段，这个设计很有意思" | 需要视觉上下文 | 截图 + 我的评论 → 归档 |
| "帮我记刚才那段" | 需要视频回溯 | Replay Buffer 取最近 15s → 归档 |
| "这个机制是怎么运作的" | 需要视觉上下文 | 截图 → 分析 → 语音回答 |
| "把刚才那段转成 GIF" | 需要视频 | Replay Buffer → 转 GIF → 告诉路径 |
| "帮我想个游戏角色名字" | 不需要截图 | 直接回答 |
| "今天的简报有什么值得关注的" | 不需要截图 | 读 Obsidian 简报 → 语音摘要 |

---

## 三、设计原则

### 1. 模块化，核心不耦合具体能力
- Core 只负责：**听懂 → 判断意图 → 路由 → 调用 → 广播**
- 新增能力 = 新增模块文件，不改核心代码（见「模块扩展标准」）
- 场景扩展（游戏 → 工作 → 智能眼镜）也通过模块实现

### 2. 奥卡姆剃刀：够用就好，不过早复杂化
- 存储：先用 Obsidian（已有，够用）
- 语音识别：本地 Whisper（离线、免费、够用）
- TTS：edge-tts（免费、中文够用）
- 录屏：d3dshot + ffmpeg（轻量，游戏兼容，无需第三方软件）
- 只有明确不满足时才引入新依赖

### 3. 隐私友好
- 感知是被动触发，不持续上传屏幕
- 所有数据默认本地存储
- AI 调用按需，不持续消耗 token

### 4. 接口解耦
- ARIA 核心不依赖任何前端/展示层
- 所有动作完成后通过 `core/bus.py` 广播事件
- 外部消费者（Godot、未来 web 界面等）监听事件，ARIA 不关心渲染

---

## 四、模块规划

### Actions（AI 能做什么）

| 模块 | 功能 | 阶段 | 状态 |
|---|---|---|---|
| `archive` | 截图 + 备注 → Obsidian md | Phase 1 | ✅ 完成 |
| `answer` | 截图 → 视觉模型分析 → 语音回答 | Phase 1 | ✅ 完成 |
| `chat` | 纯对话，不操作文件系统 | Phase 1 | ✅ 完成 |
| `replay_buffer` | 后台截帧环形队列，取最近 N 秒 | Phase 2 | 🔧 代码完成，待验证 |
| `convert` | 视频 → GIF（ffmpeg） | Phase 2 | ⬜ 待实现 |
| `browse` | 打开/摘要网页内容 | Phase 3 | ⬜ 按需接入 |
| `remind` | 设定提醒 + Windows 通知 | Phase 3 | ⬜ 按需接入 |
| `search` | 检索已归档 vault 内容 | Phase 3 | ⬜ 按需接入 |
| `read` | 读取 PDF / 网页正文 | Phase 3 | ⬜ 按需接入 |

> **注**：`capture` 模块（原 OBS 方案）已被 `perception` 层直接截图 + `replay_buffer` 模块取代，不再单独维护。

### Identity（AI 是什么）

| 模块 | 功能 | 阶段 | 状态 |
|---|---|---|---|
| `persona` | 性格配置、交互记录 | Phase 1 | ✅ 完成（基础版）|
| `voice` | edge-tts 生成 + WMP 播放 | Phase 1 | ✅ 完成 |
| `avatar` | Godot 形象对接接口 | Phase 1.5 | 🔧 接口待锁定 |

### Perception（AI 怎么感知）

| 模块 | 功能 | 阶段 | 状态 |
|---|---|---|---|
| 快捷键触发 | `keyboard` 库，`Ctrl+\`` | Phase 1 | ✅ 完成 |
| 语音录制 | `sounddevice` 静音自动停 | Phase 1 | ✅ 完成 |
| 语音识别 | `faster-whisper` 本地离线 | Phase 1 | ✅ 完成 |
| 唤醒词 | 常驻监听，手不在键盘时触发 | Phase 2 | ⬜ 待实现 |
| 场景感知 | 本地轻量视觉模型，主动检测 | Phase 3 | ⬜ 远期 |
| 硬件接入 | 智能眼镜等外部设备 | Phase 4 | ⬜ 远期 |

---

## 五、模块扩展标准

> 任何新能力只需满足以下接口，放入 `modules/actions/` 即自动被 Dispatcher 加载。

```python
# modules/actions/your_module.py

MANIFEST = {
    "name": "module_name",          # 唯一标识，对应 intent.action
    "triggers": ["触发词1", "触发词2"],  # 关键词兜底（LLM 不可用时）
    "description": "这个模块做什么",
}

def run(context: dict, config: dict) -> dict:
    """
    context 标准字段：
      transcript   str   用户原话
      timestamp    str   ISO 时间戳
      screenshot   str?  截图路径（需要时由 main 层填入）
      reply        str   intent 建议的语音回复
      + intent params 展开的字段

    返回：
      status   "ok" | "error"
      message  str   最终语音播报内容
      + 任意附加数据
    """
    ...
    return {"status": "ok", "message": "完成了"}
```

---

## 六、Godot 对接接口规范

> ARIA 只发事件，不关心 Godot 怎么渲染。由用户主导 Godot 形象设计，ARIA 配合留接口。

### 事件格式（`core/bus.py` 广播）

```python
{
  "event": "aria.action_complete",   # 事件类型
  "action": "archive",               # 执行了什么动作
  "reply": "记好了",                  # 语音回复内容（驱动口型/字幕）
  "status": "ok",                    # ok | error
  "timestamp": "2026-03-25T22:00:00",
  "data": {                          # 可选，动作相关数据
    "screenshot": "path/to/img.jpg",
    "md_path": "path/to/note.md",
    # ...
  }
}
```

### 传输方式（待定，Phase 1.5 确认）
- 候选 A：本地 WebSocket（`ws://localhost:7070`）
- 候选 B：本地 named pipe
- 候选 C：文件轮询（最简单，够用就行）

---

## 七、分阶段路线图

### ✅ Phase 1 · MVP（已完成）
- 热键触发 → Whisper 识别 → GLM-4-Flash 意图解析 → 截图 → 动作执行 → TTS 回应
- 支持动作：archive / answer / chat
- 截图优化：JPEG 压缩，压缩比 ~150×，响应 0.2–0.3s

### 🔧 Phase 1.5 · 收尾（本周）
- [ ] 游戏场景热键测试（全屏游戏中 `Ctrl+\`` 是否被拦截）
- [ ] 锁定 Godot 事件总线格式（WebSocket vs pipe vs 文件）
- [ ] 整合 CodeBuddy 分层感知设计（对话记录待提供）
- [ ] 更新 `core/bus.py` 实现事件广播

### ⬜ Phase 2 · 游戏录屏
- 验证 d3dshot 游戏全屏捕获（本地机器测试）
- 接入 `replay_buffer` 模块到主流程
- 实现 `convert` 模块（视频 → GIF）
- 录屏回溯时长：15 秒（游戏场景）

### ⬜ Phase 3 · 模块扩展
- 按需接入：browse / remind / search / read
- 标准：每个模块独立，不改核心，30 分钟内可接入
- 唤醒词支持

### ⬜ Phase 4 · Godot 形象对接
- ARIA 事件总线稳定后对接 Godot
- 用户主导形象设计（Claude Game Studio）
- ARIA 只保证事件格式稳定

### ⬜ Phase 5 · 远期
- 本地轻量视觉感知（主动检测屏幕变化）
- 硬件接入（智能眼镜等）
- 插件化能力市场

---

## 八、技术约束与边界

- **运行环境**：Windows（PowerShell），需支持全局热键
- **存储**：Obsidian vault，路径可配置
- **不做的事**（Phase 1/2）：
  - 不做 web 界面
  - 不做持续屏幕监控
  - 不做云同步（Obsidian Git 已解决）
  - 不做虚拟形象渲染（Godot 那边的事）

---

## 九、技术决策记录

| 问题 | 决策 | 理由 |
|---|---|---|
| 全局热键 | `Ctrl+\`` | 游戏场景占用少，位置顺手 |
| Phase 1 视频录制 | 不做，只截图 | 录视频方案 Phase 2 再做 |
| 录屏方案 | d3dshot + ffmpeg，排除 OBS | OBS 太笨重；d3dshot 走 DXGI，游戏兼容好 |
| 录屏回溯时长 | 15 秒 | 游戏操作场景够用，文档场景直接截屏 |
| 意图模型 | GLM-4-Flash（兼容 OpenAI API） | 免费额度，延迟低 |
| 视觉模型 | Gemini 2.0 Flash Vision | 免费，效果好 |
| TTS | edge-tts + WMP COM 播放 | 免费，中文够用，无额外依赖 |
| Obsidian vault | `data/vault`（项目内，当前够用） | 后续可迁移独立 vault |
| Godot 形象 | 用户主导，ARIA 留事件接口 | 完全解耦，互不阻塞 |
| 模块扩展 | 热插拔，MANIFEST + run 接口 | 不改核心，按需加入 |

---

## 十、开放问题

| 问题 | 状态 |
|---|---|
| Godot 事件总线传输方式（WebSocket / pipe / 文件） | 🔧 Phase 1.5 确认 |
| CodeBuddy 分层感知设计整合 | 🔧 等对话记录 |
| d3dshot 游戏全屏捕获验证 | 🔧 等本地测试结果 |
| 游戏热键冲突测试 | 🔧 等本地测试结果 |
