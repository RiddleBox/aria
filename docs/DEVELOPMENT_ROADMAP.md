# ARIA 开发路线图

> 版本：v1.1 · 2026-03-25（基于 PRD v0.1 + Phase 1 实际进展更新）
> 状态：Phase 1 核心流程已验证，进入 Phase 1 收尾

---

## 📊 当前状态（Phase 1 实际完成情况）

### ✅ 已跑通的核心流程
| 功能 | 实现方式 | 状态 |
|---|---|---|
| 全局热键触发 | `keyboard` 库，`Ctrl+\`` | ✅ |
| 语音录制 | `sounddevice`，静音自动停 | ✅ |
| 语音识别 | `faster-whisper` base 模型，本地离线 | ✅ |
| 意图解析 | GLM-4-Flash（兼容 OpenAI 格式） | ✅ |
| 截图 | `mss` + `cv2` JPEG 压缩（压缩比 ~150x） | ✅ |
| 视觉分析 | Gemini 2.0 Flash Vision | ✅ |
| 动作归档 | 写入 Obsidian vault `.md` + 嵌入截图 | ✅ |
| 语音回应 | `edge-tts` 生成 mp3，WMP COM 播放 | ✅ |
| Persona | 性格配置 + 交互记录 | ✅（基础版）|

### 📈 截图性能指标
| 指标 | 数值 |
|---|---|
| 截图响应时间 | 0.2–0.3 秒 |
| 文件大小（1440p→1080p JPEG） | ~71 KB（原 PNG ~537 KB） |
| 压缩比 | ~151× |

### ⚠️ Phase 1 尚未验收的项
- [ ] 游戏中热键不被拦截（待实际游戏场景测试）
- [ ] 录视频方案（待专项调研，见下方）

---

## 🎯 Phase 1 收尾（当前，1–2 周）

### 1. 游戏兼容性测试
- 在全屏游戏（如 Warframe、CS2）中测试 `Ctrl+\`` 是否被拦截
- 如有冲突，评估备选热键或改用鼠标侧键

### 2. 录视频方案选型（专项调研）
> PRD 明确：OBS 太笨重，需调研轻量方案。候选见下方「录视频方案调研」章节。

---

## 🔮 Phase 2 · 扩展（Phase 1 收尾后）

### 2.1 录视频 + Replay Buffer
- 目标：说"帮我记刚才那段" → 保存过去 N 秒视频片段
- 依赖：录视频方案选型结论
- 顺带：`convert` 模块（视频→GIF，ffmpeg）

### 2.2 更自然的交互
- 唤醒词支持（日常工作场景，手不在键盘时）
- 本地轻量视觉感知（场景变化检测，Phase 2 被动感知）

### 2.3 更多 Action 模块
| 模块 | 功能 | 备注 |
|---|---|---|
| `convert` | 视频→GIF | 依赖录视频方案 |
| `browse` | 打开/摘要网页 | 独立，可提前做 |
| `remind` | 设定提醒 | 独立，可提前做 |
| `search` | 检索归档内容 | 依赖积累足够数据后才有价值 |

---

## 🚀 Phase 3 · 未来

- 虚拟形象（屏幕角落小角色）
- 智能眼镜硬件接入
- 本地轻量视觉模型（主动感知屏幕变化）

---

## 🎬 录视频方案调研

> PRD 开放问题 #1，Phase 2 前必须选定

### 候选方案对比

| 方案 | 原理 | 游戏兼容性 | 性能开销 | 实现复杂度 | 是否需要第三方软件 |
|---|---|---|---|---|---|
| **ffmpeg screen capture** | `gdigrab`（GDI）或 `dshow` | ❌ 游戏差（GDI 无法捕获 D3D） | 中 | 低 | 需要 ffmpeg（已有） |
| **DXGI Desktop Duplication** | Windows D3D11 原生 API | ✅ 游戏最佳 | 极低 | 高（需 C 扩展或 d3dshot） | 无 |
| **d3dshot** | DXGI 的 Python 封装 | ✅ | 低 | 低 | 无（pip 安装） |
| **OBS obs-cli / websocket** | OBS 无界面/后台模式 | ✅ | 中高 | 中 | 需要 OBS 安装 |
| **mss + ffmpeg 编码** | mss 截帧 + ffmpeg 拼视频 | ⚠️ 一般（同 GDI） | 中 | 低 | 需要 ffmpeg |

### 推荐结论

**首选：`d3dshot` + ffmpeg 后处理**
- `d3dshot` 底层用 DXGI，游戏兼容性好，pip 可装
- 配合 ffmpeg 做 Replay Buffer（环形内存写入，触发时落盘）
- 无需安装任何第三方桌面软件，符合"不重新造轮子"原则

**备选：`mss` 帧序列 + ffmpeg**
- mss 已有，截帧速度快，但 GDI 捕获游戏全屏可能黑屏
- 适合非游戏场景（工作、阅读、视频）

**排除：OBS**
- 太重，用户体验差，PRD 已明确排除

### 下一步行动
1. `pip install d3dshot` 测试能否捕获游戏画面
2. 实现简单 Replay Buffer：后台每秒截 5 帧，环形队列保留 30 秒，触发时用 ffmpeg 合成 mp4
3. 验收：游戏内说"帮我记刚才那段" → 生成 30s mp4 → 归档

---

## 📋 决策记录（与 PRD 保持同步）

| 问题 | 决策 | 理由 |
|---|---|---|
| 热键 | `Ctrl+\`` | 游戏场景占用少，位置顺手 |
| Phase 1 视频 | 不做，只截图 | 录视频方案待选型 |
| TTS | edge-tts + WMP COM 播放 | 免费、中文够用、无 pydub 依赖 |
| 意图模型 | GLM-4-Flash（兼容 OpenAI API） | 免费额度，延迟低 |
| 视觉模型 | Gemini 2.0 Flash Vision | 免费，效果强于 GPT-4o-mini-vision |
| Obsidian vault | `data/vault`（项目内） | 当前够用，后续迁移独立 vault |
| 录视频方案 | 待定，首选 d3dshot | OBS 已排除 |
