# ARIA — AI Runtime Interface Agent

> 语音驱动的模块化个人助手终端

## 核心理念

**Core 只负责三件事：听懂 → 找到谁做 → 调用。**

具体能做什么、长什么样、有什么性格，全部通过模块实现。模块可以随时插拔。

## 项目结构

```
aria/
├── core/                   # 核心引擎（不轻易改动）
│   ├── perception.py       # 感知层：语音识别、唤醒词
│   ├── intent.py           # 意图层：LLM 解析指令 → 路由到模块
│   ├── dispatcher.py       # 调度层：找到对应模块并执行
│   └── bus.py              # 事件总线：模块间通信
│
├── modules/
│   ├── actions/            # Action 模块：AI 能做什么
│   │   ├── capture.py      # 截图 + 录屏（OBS Replay Buffer）
│   │   ├── archive.py      # 文档归档（写入 Obsidian md）
│   │   └── convert.py      # 媒体转换（视频→GIF，ffmpeg）
│   │
│   └── identity/           # Identity 模块：AI 是什么
│       ├── persona.py      # 性格 / 记忆 / 对话风格
│       ├── voice.py        # 音色 / 语气（TTS）
│       └── avatar.py       # 虚拟形象（预留）
│
├── config/
│   ├── settings.yaml       # 全局配置
│   └── modules.yaml        # 模块注册表
│
├── data/
│   ├── captures/           # 截图 / 视频 / GIF 存放
│   └── archive/            # 归档的 md 文档
│
└── main.py                 # 启动入口
```

## 模块规范

每个 Action 模块必须实现：
```python
MANIFEST = {
    "name": "模块名",
    "triggers": ["关键词1", "关键词2"],   # 触发词（供 intent 路由）
    "description": "这个模块做什么",
}

def run(context: dict) -> dict:
    # context 包含：transcript（语音文字）、screenshot、timestamp 等
    # 返回：{"status": "ok", "message": "回复给用户的话", ...}
    ...
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置
cp config/settings.yaml.example config/settings.yaml
# 编辑 settings.yaml，填入 API key 等

# 启动
python main.py
```

## 当前模块状态

| 模块 | 类型 | 状态 |
|------|------|------|
| capture | action | ✅ MVP |
| archive | action | ✅ MVP |
| convert | action | ✅ MVP |
| persona | identity | 🚧 基础版 |
| voice | identity | 🚧 基础版 |
| avatar | identity | 📋 预留 |
