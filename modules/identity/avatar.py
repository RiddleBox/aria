"""
modules/identity/avatar.py — 虚拟形象模块（预留）
目前只是占位，未来可接入 VTube Studio / Live2D / Electron 窗口
"""

MANIFEST = {
    "name": "avatar",
    "triggers": [],
    "description": "Aria 的虚拟形象（预留，未实现）",
}

# ── 未来扩展方向 ──────────────────────────────────────
#
# 方案A（轻量）：Electron 窗口 + CSS 动画
#   - 一个透明置顶窗口
#   - 说话时嘴巴动，待机时待机动画
#   - 实现：Python 控制 Electron via WebSocket
#
# 方案B（完整）：VTube Studio + Live2D 模型
#   - 接入 VTube Studio API（WebSocket，端口 8001）
#   - 控制表情、动作
#   - 需要一个 Live2D 模型文件
#
# 方案C（最简）：系统托盘图标动画
#   - 用 pystray + PIL 实现不同状态的图标
#   - 超轻量，无需额外窗口
#
# ─────────────────────────────────────────────────────


class Avatar:
    """虚拟形象控制器（占位）。"""

    def set_state(self, state: str):
        """
        state: idle | listening | speaking | thinking
        """
        print(f"[Avatar] State: {state} (not implemented)")

    def show(self):
        print("[Avatar] Show (not implemented)")

    def hide(self):
        print("[Avatar] Hide (not implemented)")


def run(context: dict, config: dict) -> dict:
    return {"status": "ok", "message": ""}
