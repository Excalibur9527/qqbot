"""
赛博敲木鱼插件
指令：/敲木鱼、/木鱼、/muyu、/敲
功能：累加功德值，有暴击和负面效果，每日排行榜，支持事件系统
"""

import random
import re
import time
from typing import Dict, List, Tuple
from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.log import logger

from plugins.unified_db import unified_db
from plugins.event_service import event_service
from plugins.title_service import title_service


# 敲木鱼结果配置 (delta, weight, message)
# 调整后：基础收益提高，负面概率降低
KNOCK_RESULTS = [
    # 正常收益（提高基础值）
    (2, 50, "🪵 咚~ 功德 +2"),
    (3, 30, "🪵 咚咚~ 功德 +3"),
    (5, 20, "🪵 咚咚咚~ 功德 +5"),
    (8, 10, "✨ 木鱼微微发光~ 功德 +8"),
    
    # 小暴击
    (15, 5, "🌟 佛光乍现！功德 +15"),
    (25, 2, "💫 佛祖微微点头~ 功德 +25"),
    
    # 大暴击（极低概率）
    (50, 0.5, "🎆 佛祖显灵！！功德 +50！"),
    (100, 0.2, "🌈 超级暴击！！！功德 +100！！！"),
    (233, 0.05, "👼 天降神迹！！！功德 +233！！！！"),
    
    # 负面效果（降低概率和惩罚）
    (-1, 3, "💨 敲歪了...功德 -1"),
    (-2, 2, "😅 手滑了...功德 -2"),
    (-3, 1, "💥 木鱼敲裂了...功德 -3"),
    (-5, 0.5, "😱 木鱼碎了！功德 -5"),
    (-10, 0.2, "🔥 木鱼着火了！！功德 -10"),
    (-20, 0.05, "💀 惊动了佛祖...功德 -20"),
    
    # 奇怪效果（零收益）
    (0, 5, "🤔 木鱼发出了奇怪的声音...功德 +0"),
    (0, 3, "👻 木鱼里好像有东西...功德 +0"),
    (0, 2, "🌀 你陷入了沉思...功德 +0"),
    (0, 1, "😴 你敲着敲着睡着了...功德 +0"),
    (0, 0.5, "🐱 一只猫跳上了木鱼...功德 +0"),
    
    # 特殊效果
    (7, 3, "🎰 幸运数字7！功德 +7"),
    (-7, 0.3, "🎰 不幸数字7...功德 -7"),
    (13, 1, "🌙 神秘数字13！功德 +13"),
    (-13, 0.1, "🌑 不祥数字13...功德 -13"),
    (66, 0.3, "😈 六六大顺！功德 +66"),
    (-66, 0.02, "👿 六六大凶...功德 -66"),
    (88, 0.2, "🧧 发发发！功德 +88"),
    (114514, 0.01, "🤣 哼哼哼啊啊啊啊啊！功德 +114514"),
]


def get_knock_result(merit_bonus: int = 0) -> Tuple[int, str]:
    """根据权重随机获取敲木鱼结果"""
    # 如果有功德大爆发事件，固定+10
    if merit_bonus > 0:
        return merit_bonus, f"💥 功德大爆发！功德 +{merit_bonus}"
    
    total_weight = sum(r[1] for r in KNOCK_RESULTS)
    rand = random.uniform(0, total_weight)
    current = 0
    for delta, weight, msg in KNOCK_RESULTS:
        current += weight
        if rand <= current:
            return delta, msg
    return 1, "🪵 咚~ 功德 +1"


# 注册命令
knock_cmd = on_regex(r"^[\x00-\x1f]*[/／]?(敲木鱼|木鱼|muyu|敲+)\s*$", priority=5, block=True)
merit_rank_cmd = on_command("功德榜", aliases={"功德排行", "今日功德榜"}, priority=5, block=True)
total_merit_cmd = on_command("总功德榜", aliases={"功德总榜"}, priority=5, block=True)
my_merit_cmd = on_command("我的功德", aliases={"功德", "查功德"}, priority=5, block=True)

# 防刷记录
knock_history: Dict[Tuple[str, str], List[float]] = {}


def count_knock_chars(text: str) -> int:
    """统计命令中'敲'字的数量"""
    return text.count("敲")


def check_spam(group_id: str, user_id: str) -> Tuple[int, int]:
    """检查是否刷屏（10秒内超过3次）"""
    global knock_history
    key = (group_id, user_id)
    now = time.time()
    
    if key not in knock_history:
        knock_history[key] = []
    
    knock_history[key] = [t for t in knock_history[key] if now - t < 10]
    knock_history[key].append(now)
    
    count = len(knock_history[key])
    if count > 3:
        penalty = (count - 3) * 2
        return penalty, count
    return 0, count


@knock_cmd.handle()
async def handle_knock(bot: Bot, event: Event):
    """敲木鱼"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await knock_cmd.finish("请在群里敲木鱼喵~")
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        # 获取原始消息文本
        raw_text = event.get_plaintext().strip()
        raw_text = re.sub(r'[\x00-\x1f]', '', raw_text)
        
        # 检查多个"敲"字
        knock_count = count_knock_chars(raw_text)
        if knock_count > 1:
            penalty = knock_count - 1
            today_merit, total_merit = unified_db.update_merit(group_id, user_id, nickname, -penalty)
            result = f"🚫 贪心敲了{knock_count}下！功德 -{penalty}\n今日功德: {today_merit} | 总功德: {total_merit}"
            await knock_cmd.finish(Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {result}")
            ]))
            return
        
        # 检查刷屏
        spam_penalty, spam_count = check_spam(group_id, user_id)
        if spam_penalty > 0:
            today_merit, total_merit = unified_db.update_merit(group_id, user_id, nickname, -spam_penalty)
            result = f"🚫 敲太快了！10秒内已敲{spam_count}次！功德 -{spam_penalty}\n今日功德: {today_merit} | 总功德: {total_merit}"
            await knock_cmd.finish(Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {result}")
            ]))
            return
        
        # 检查事件效果
        effects = event_service.get_active_effects(group_id)
        merit_bonus = effects.get("merit_bonus", 0)
        
        # 正常敲木鱼
        delta, msg = get_knock_result(merit_bonus)
        today_merit, total_merit = unified_db.update_merit(group_id, user_id, nickname, delta)
        
        result = f"{msg}\n今日功德: {today_merit} | 总功德: {total_merit}"
        
        # 检查头衔解锁
        new_titles = title_service.check_and_unlock(group_id, user_id)
        if new_titles:
            result += f"\n\n🏆 解锁新头衔：{', '.join(new_titles)}"
            for title in new_titles:
                await title_service.set_qq_title(bot, group_id, user_id, title)
        
        await knock_cmd.finish(Message([
            MessageSegment.at(user_id),
            MessageSegment.text(f" {result}")
        ]))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"敲木鱼异常: {e}")


@merit_rank_cmd.handle()
async def handle_merit_rank(bot: Bot, event: Event):
    """今日功德排行榜"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        group_id = str(event.group_id)
        ranking = unified_db.get_merit_ranking(group_id, "today")
        
        if not ranking:
            await merit_rank_cmd.finish("今天还没人敲木鱼喵~")
            return
        
        lines = ["📿 今日功德排行榜 📿\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, r in enumerate(ranking):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{medal} {r['nickname']}: {r['merit']} 功德")
        
        await merit_rank_cmd.finish("\n".join(lines))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"功德榜异常: {e}")


@total_merit_cmd.handle()
async def handle_total_merit(bot: Bot, event: Event):
    """总功德排行榜"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        group_id = str(event.group_id)
        ranking = unified_db.get_merit_ranking(group_id, "total")
        
        if not ranking:
            await total_merit_cmd.finish("还没人积累功德喵~")
            return
        
        lines = ["🏆 总功德排行榜 🏆\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, r in enumerate(ranking):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{medal} {r['nickname']}: {r['merit']} 功德")
        
        await total_merit_cmd.finish("\n".join(lines))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"总功德榜异常: {e}")


@my_merit_cmd.handle()
async def handle_my_merit(bot: Bot, event: Event):
    """查看我的功德"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        user = unified_db.get_or_create_user(group_id, user_id, nickname)
        
        lines = [f"📿 {nickname} 的功德"]
        lines.append(f"今日功德: {user.today_merit}")
        lines.append(f"总功德: {user.total_merit}")
        lines.append(f"敲木鱼次数: {user.knock_count}")
        
        if user.current_title:
            lines.append(f"当前头衔: 【{user.current_title}】")
        
        await my_merit_cmd.finish(Message([
            MessageSegment.at(user_id),
            MessageSegment.text(f"\n" + "\n".join(lines))
        ]))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"查功德异常: {e}")


# 为了兼容旧代码，提供 woodfish_db 接口
class WoodfishDBCompat:
    """兼容旧接口"""
    def deduct_merit(self, group_id: str, user_id: str, nickname: str, amount: int = 10):
        return unified_db.deduct_merit(group_id, user_id, nickname, amount)

woodfish_db = WoodfishDBCompat()
