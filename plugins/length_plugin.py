"""
牛子长度插件 - 随机生成长度并回复有趣内容
每天8点刷新，同一天同一人结果固定
使用统一数据库存储长度数据
"""

import random
import hashlib
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.params import CommandArg
from nonebot.rule import to_me
from nonebot.log import logger

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from plugins.daily_utils import get_daily_seed
from plugins.unified_db import unified_db


def get_daily_length(user_id: str, group_id: str = "") -> int:
    """
    获取今日长度（8点刷新）
    优先从数据库读取，如果没有则生成并存储
    """
    # 尝试从数据库获取
    user = unified_db.get_user(group_id, user_id)
    if user and user.today_length is not None:
        return user.today_length
    
    # 生成新的长度
    seed_str = get_daily_seed(user_id, group_id)
    seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    rng = random.Random(seed)
    length = rng.randint(-30, 30)
    
    # 存储到数据库
    unified_db.update_length(group_id, user_id, length)
    
    return length


def get_length_reply(length: int) -> str:
    """根据长度生成回复内容"""
    if length < -20:
        replies = [
            f"今天你的长度是{length}cm，是小小男娘喔~",
            f"哎呀{length}cm，这也太小了，小男娘要加油啊！",
            f"{length}cm的长度，今天是平胸小男娘模式吗？",
            f"今天只有{length}cm，小小的一只，男娘属性MAX！"
        ]
    elif length < -10:
        replies = [
            f"今天你的长度是{length}cm，是小男娘喔~",
            f"{length}cm，不错的小男娘身材呢！",
            f"今天是{length}cm，小男娘模式启动！",
            f"{length}cm的长度，很可爱的男娘尺寸~"
        ]
    elif length < 0:
        replies = [
            f"今天你的长度是{length}cm，是伪娘喔~",
            f"{length}cm，今天是伪娘模式吗？",
            f"哎呀{length}cm，是可爱的伪娘呢！",
            f"{length}cm的长度，伪娘属性有点强~"
        ]
    elif length == 0:
        replies = [
            "今天你的长度是0cm，完全平了呢！",
            "0cm，今天是平板模式吗？",
            "今天完全是0cm，平板伪娘！",
            "0cm的长度，今天是纯平板呢~"
        ]
    elif length <= 10:
        replies = [
            f"今天你的长度是{length}cm，小小的一根呢~",
            f"{length}cm，今天是迷你尺寸吗？",
            f"哎呀{length}cm，小巧可爱呢！",
            f"{length}cm的长度，很可爱的小尺寸~"
        ]
    elif length <= 20:
        replies = [
            f"今天你的长度是{length}cm，标准尺寸呢~",
            f"{length}cm，今天是普通模式吗？",
            f"不错哦{length}cm，很标准的长度！",
            f"{length}cm的长度，正好合适呢~"
        ]
    else:
        replies = [
            f"今天你的长度是{length}cm，好长..",
            f"哇{length}cm，这么长的大宝贝！",
            f"{length}cm，今天是大长腿模式吗？",
            f"好家伙{length}cm，长得吓人啊！"
        ]

    return random.choice(replies)


# 创建命令处理器 - 提高优先级
length_cmd = on_command("今日长度", priority=1, block=False)

# 创建@机器人处理器 - 优先级高于AI插件，确保长度查询优先处理
length_at = on_message(rule=to_me(), priority=2, block=False)


@length_cmd.handle()
async def handle_length_command(bot: Bot, event: Event):
    """处理"今日长度"命令"""
    try:
        user_id = event.get_user_id()
        group_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else ""

        # 生成今日固定长度（8点刷新）
        length = get_daily_length(user_id, group_id)
        reply_text = get_length_reply(length)

        # 构建回复消息
        reply = Message([
            MessageSegment.at(user_id),
            MessageSegment.text(f" {reply_text}")
        ])

        await length_cmd.finish(reply)
        logger.info(f"回复长度查询: 用户 {user_id}, 长度 {length}cm")

    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"长度查询处理失败: {e}")


@length_at.handle()
async def handle_length_at(bot: Bot, event: Event):
    """处理@机器人消息 - 只处理纯@消息"""
    try:
        # 只处理群消息
        if not isinstance(event, GroupMessageEvent):
            return

        user_id = event.get_user_id()
        group_id = str(event.group_id)
        message = event.get_message()

        # 获取纯文本内容
        text_content = ""
        for segment in message:
            if segment.type == "text":
                text_content += segment.data.get("text", "").strip()

        # 如果只有@机器人，没有其他内容或者内容是空白的，就回复长度
        if len(message) == 1 and message[0].type == "at":
            # 生成今日固定长度（8点刷新）
            length = get_daily_length(user_id, group_id)
            reply_text = get_length_reply(length)

            # 构建回复消息
            reply = Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {reply_text}")
            ])

            await length_at.finish(reply)
            logger.info(f"回复纯@消息: 用户 {user_id}, 长度 {length}cm")

        # 如果是@机器人 + "今日长度"，也在这里处理，避免命令处理器冲突
        elif text_content.strip() == "今日长度":
            # 生成今日固定长度（8点刷新）
            length = get_daily_length(user_id, group_id)
            reply_text = get_length_reply(length)

            # 构建回复消息
            reply = Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {reply_text}")
            ])

            await length_at.finish(reply)
            logger.info(f"回复@今日长度: 用户 {user_id}, 长度 {length}cm")

    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"@消息处理失败: {e}")
