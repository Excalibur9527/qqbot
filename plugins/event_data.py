"""
随机事件数据定义
包含20+种随机事件：全局正面、全局负面、个人正面、个人负面、特殊事件
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class EventType(Enum):
    GLOBAL_POSITIVE = "global_positive"    # 全局正面
    GLOBAL_NEGATIVE = "global_negative"    # 全局负面
    PERSONAL_POSITIVE = "personal_positive" # 个人正面
    PERSONAL_NEGATIVE = "personal_negative" # 个人负面
    SPECIAL = "special"                     # 特殊事件


@dataclass
class Event:
    """事件数据"""
    id: str                    # 唯一标识
    name: str                  # 显示名称
    event_type: EventType      # 事件类型
    duration: int              # 持续时间(秒)，0表示即时效果
    description: str           # 描述
    effects: Dict[str, Any]    # 效果参数
    emoji: str = "🎲"          # 显示emoji
    weight: float = 1.0        # 触发权重
    message: str = ""          # 触发时的消息模板
    
    def is_global(self) -> bool:
        return self.event_type in [EventType.GLOBAL_POSITIVE, EventType.GLOBAL_NEGATIVE, EventType.SPECIAL]


# ========== 全局正面事件 ==========
GLOBAL_POSITIVE_EVENTS = [
    Event(
        "merit_explosion", "功德大爆发", EventType.GLOBAL_POSITIVE, 60,
        "1分钟内敲木鱼固定+10功德",
        {"merit_bonus": 10},
        "💥", 1.0,
        "🎉 【功德大爆发】{nickname} 触发了功德大爆发！1分钟内所有人敲木鱼固定+10功德！"
    ),
    Event(
        "fish_migration", "鱼群迁徙", EventType.GLOBAL_POSITIVE, 300,
        "5分钟内稀有鱼概率翻倍",
        {"rare_multiplier": 2},
        "🐟", 1.0,
        "🌊 【鱼群迁徙】{nickname} 发现了鱼群迁徙！5分钟内稀有鱼概率翻倍！"
    ),
    Event(
        "golden_hour", "黄金时刻", EventType.GLOBAL_POSITIVE, 180,
        "3分钟内闪光鱼概率翻倍",
        {"shiny_multiplier": 2},
        "✨", 0.8,
        "🌟 【黄金时刻】{nickname} 开启了黄金时刻！3分钟内闪光鱼概率翻倍！"
    ),
    Event(
        "blessing", "佛祖庇佑", EventType.GLOBAL_POSITIVE, 120,
        "2分钟内不会钓到暗黑鱼",
        {"no_dark": True},
        "🙏", 0.8,
        "🙏 【佛祖庇佑】{nickname} 获得佛祖庇佑！2分钟内所有人不会钓到暗黑鱼！"
    ),
    Event(
        "double_catch", "双倍收获", EventType.GLOBAL_POSITIVE, 120,
        "2分钟内每次钓鱼获得两条",
        {"double": True},
        "🎣", 0.6,
        "🎣 【双倍收获】{nickname} 触发了双倍收获！2分钟内每次钓鱼获得两条鱼！"
    ),
    Event(
        "size_festival", "巨型鱼出没", EventType.GLOBAL_POSITIVE, 180,
        "3分钟内所有鱼长度+50%",
        {"global_size_multiplier": 1.5},
        "📏", 0.7,
        "📏 【巨型鱼出没】{nickname} 发现巨型鱼群！3分钟内所有鱼长度+50%！"
    ),
    Event(
        "merit_rain", "功德雨", EventType.GLOBAL_POSITIVE, 60,
        "1分钟内每次钓鱼额外获得1-5功德",
        {"merit_range": [1, 5]},
        "🌧️", 0.8,
        "🌧️ 【功德雨】{nickname} 召唤了功德雨！1分钟内每次钓鱼额外获得1-5功德！"
    ),
]

# ========== 全局负面事件 ==========
GLOBAL_NEGATIVE_EVENTS = [
    Event(
        "pollution", "河水污染", EventType.GLOBAL_NEGATIVE, 600,
        "10分钟内只能钓到暗黑鱼",
        {"dark_only": True},
        "☠️", 0.5,
        "☠️ 【河水污染】{nickname} 不小心污染了河水！10分钟内所有人只能钓到暗黑鱼！"
    ),
    Event(
        "drought", "河水干涸", EventType.GLOBAL_NEGATIVE, 300,
        "5分钟内钓鱼消耗翻倍",
        {"cost_multiplier": 2},
        "🏜️", 0.6,
        "🏜️ 【河水干涸】{nickname} 触发了河水干涸！5分钟内钓鱼消耗翻倍！"
    ),
    Event(
        "storm", "暴风雨", EventType.GLOBAL_NEGATIVE, 180,
        "3分钟内无法钓鱼",
        {"no_fishing": True},
        "⛈️", 0.4,
        "⛈️ 【暴风雨】{nickname} 引来了暴风雨！3分钟内所有人无法钓鱼！"
    ),
    Event(
        "fish_escape", "鱼群逃离", EventType.GLOBAL_NEGATIVE, 180,
        "3分钟内稀有鱼概率减半",
        {"rare_multiplier": 0.5},
        "💨", 0.7,
        "💨 【鱼群逃离】{nickname} 吓跑了鱼群！3分钟内稀有鱼概率减半！"
    ),
    Event(
        "curse_spread", "诅咒蔓延", EventType.GLOBAL_NEGATIVE, 120,
        "2分钟内暗黑鱼概率翻倍",
        {"dark_multiplier": 2},
        "👻", 0.6,
        "👻 【诅咒蔓延】{nickname} 释放了诅咒！2分钟内暗黑鱼概率翻倍！"
    ),
]

# ========== 个人正面事件 ==========
PERSONAL_POSITIVE_EVENTS = [
    Event(
        "lucky_catch", "幸运一击", EventType.PERSONAL_POSITIVE, 0,
        "本次必定钓到稀有+",
        {"guaranteed_rare": True},
        "🍀", 1.0,
        "🍀 {nickname} 触发了【幸运一击】！本次必定钓到稀有以上的鱼！"
    ),
    Event(
        "bonus_fish", "意外收获", EventType.PERSONAL_POSITIVE, 0,
        "额外获得一条鱼",
        {"extra_fish": True},
        "🎁", 1.2,
        "🎁 {nickname} 获得了【意外收获】！额外钓到一条鱼！"
    ),
    Event(
        "personal_merit", "功德加持", EventType.PERSONAL_POSITIVE, 0,
        "获得5-20点功德",
        {"merit_range": [5, 20]},
        "🙏", 1.0,
        "🙏 {nickname} 获得了【功德加持】！获得{merit}点功德！"
    ),
    Event(
        "size_boost", "巨大化", EventType.PERSONAL_POSITIVE, 0,
        "本次鱼长度+50%",
        {"size_multiplier": 1.5},
        "📏", 1.2,
        "📏 {nickname} 触发了【巨大化】！本次钓到的鱼长度+50%！"
    ),
    Event(
        "shiny_blessing", "闪光祝福", EventType.PERSONAL_POSITIVE, 0,
        "本次必定闪光",
        {"guaranteed_shiny": True},
        "✨", 0.5,
        "✨ {nickname} 获得了【闪光祝福】！本次必定钓到闪光鱼！"
    ),
    Event(
        "free_bait", "免费打窝", EventType.PERSONAL_POSITIVE, 0,
        "获得一次免费打窝",
        {"free_bait": True},
        "🪣", 0.8,
        "🪣 {nickname} 获得了【免费打窝】！下次打窝不消耗功德！"
    ),
    Event(
        "treasure_chest", "宝箱", EventType.PERSONAL_POSITIVE, 0,
        "获得10-50点功德",
        {"merit_range": [10, 50]},
        "📦", 0.4,
        "📦 {nickname} 钓到了一个【宝箱】！获得{merit}点功德！"
    ),
    Event(
        "ancient_relic", "远古遗物", EventType.PERSONAL_POSITIVE, 0,
        "获得30-100点功德",
        {"merit_range": [30, 100]},
        "🏺", 0.2,
        "🏺 {nickname} 钓到了【远古遗物】！获得{merit}点功德！"
    ),
]

# ========== 个人负面事件 ==========
PERSONAL_NEGATIVE_EVENTS = [
    Event(
        "rod_break", "钓竿断裂", EventType.PERSONAL_NEGATIVE, 0,
        "损失5点功德",
        {"merit_loss": 5},
        "💔", 1.0,
        "💔 {nickname} 的【钓竿断裂】了！损失5点功德！"
    ),
    Event(
        "fish_got_away", "鱼跑了", EventType.PERSONAL_NEGATIVE, 0,
        "本次钓鱼失败",
        {"fail": True},
        "😢", 1.2,
        "😢 {nickname} 的鱼【跑了】！本次钓鱼失败！"
    ),
    Event(
        "cursed", "被诅咒", EventType.PERSONAL_NEGATIVE, 0,
        "下3次只能钓暗黑鱼",
        {"curse_count": 3},
        "👻", 0.5,
        "👻 {nickname} 被【诅咒】了！下3次只能钓到暗黑鱼！"
    ),
    Event(
        "slippery", "手滑了", EventType.PERSONAL_NEGATIVE, 0,
        "损失1-5点功德",
        {"merit_loss_range": [1, 5]},
        "🫠", 1.5,
        "🫠 {nickname}【手滑了】！损失{merit}点功德！"
    ),
    Event(
        "hook_stuck", "鱼钩卡住", EventType.PERSONAL_NEGATIVE, 0,
        "损失3点功德",
        {"merit_loss": 3},
        "🪝", 1.0,
        "🪝 {nickname} 的【鱼钩卡住】了！损失3点功德！"
    ),
    Event(
        "bait_stolen", "鱼饵被偷", EventType.PERSONAL_NEGATIVE, 0,
        "损失2点功德",
        {"merit_loss": 2},
        "🐭", 1.2,
        "🐭 {nickname} 的【鱼饵被偷】了！损失2点功德！"
    ),
    Event(
        "bad_luck", "霉运缠身", EventType.PERSONAL_NEGATIVE, 0,
        "下次钓鱼必定失败",
        {"next_fail": True},
        "🌧️", 0.6,
        "🌧️ {nickname} 【霉运缠身】！下次钓鱼必定失败！"
    ),
]

# ========== 特殊事件 ==========
SPECIAL_EVENTS = [
    Event(
        "time_warp", "时空扭曲", EventType.SPECIAL, 300,
        "5分钟内可钓到任意时间的鱼",
        {"all_time": True},
        "🌀", 0.3,
        "🌀 【时空扭曲】{nickname} 扭曲了时空！5分钟内可以钓到任意时间的鱼！"
    ),
    Event(
        "legendary_appear", "传说降临", EventType.SPECIAL, 60,
        "1分钟内传说鱼概率大幅提升",
        {"legendary_multiplier": 5},
        "👑", 0.2,
        "👑 【传说降临】{nickname} 召唤了传说！1分钟内传说鱼概率大幅提升！"
    ),
    Event(
        "chaos", "混沌", EventType.SPECIAL, 120,
        "2分钟内所有概率随机化",
        {"chaos": True},
        "🎲", 0.3,
        "🎲 【混沌】{nickname} 引发了混沌！2分钟内所有概率完全随机！"
    ),
    Event(
        "mirror_world", "镜像世界", EventType.SPECIAL, 180,
        "3分钟内暗黑鱼变闪光，闪光变暗黑",
        {"mirror": True},
        "🪞", 0.2,
        "🪞 【镜像世界】{nickname} 开启了镜像世界！3分钟内暗黑鱼变闪光，闪光变暗黑！"
    ),
]

# ========== 汇总所有事件 ==========
ALL_EVENTS: List[Event] = (
    GLOBAL_POSITIVE_EVENTS + 
    GLOBAL_NEGATIVE_EVENTS + 
    PERSONAL_POSITIVE_EVENTS + 
    PERSONAL_NEGATIVE_EVENTS + 
    SPECIAL_EVENTS
)

EVENT_BY_ID = {event.id: event for event in ALL_EVENTS}
GLOBAL_EVENTS = [e for e in ALL_EVENTS if e.is_global()]
PERSONAL_EVENTS = [e for e in ALL_EVENTS if not e.is_global()]


def get_event_by_id(event_id: str) -> Optional[Event]:
    """根据ID获取事件"""
    return EVENT_BY_ID.get(event_id)


def validate_events():
    """验证事件数据"""
    print(f"总事件数量: {len(ALL_EVENTS)}")
    print(f"全局正面: {len(GLOBAL_POSITIVE_EVENTS)}")
    print(f"全局负面: {len(GLOBAL_NEGATIVE_EVENTS)}")
    print(f"个人正面: {len(PERSONAL_POSITIVE_EVENTS)}")
    print(f"个人负面: {len(PERSONAL_NEGATIVE_EVENTS)}")
    print(f"特殊事件: {len(SPECIAL_EVENTS)}")
    return len(ALL_EVENTS) >= 20


if __name__ == "__main__":
    validate_events()
