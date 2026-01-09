"""
测试插件 - 对应原有的"测试"功能
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg
from nonebot.rule import to_me
from nonebot.log import logger

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

# 创建测试命令处理器
test_cmd = on_command("测试", rule=to_me(), priority=5, block=True)


@test_cmd.handle()
async def handle_test(bot: Bot, event: Event):
    """处理测试命令"""
    try:
        user_id = event.get_user_id()

        # 构建回复消息
        reply = Message([
            MessageSegment.at(user_id),
            MessageSegment.text(" 这里的风景不错，我在！")
        ])

        await test_cmd.finish(reply)
        logger.info(f"回复测试命令: 用户 {user_id}")

    except Exception as e:
        logger.error(f"测试命令处理失败: {e}")
        await test_cmd.finish("测试功能出错了，请稍后再试")
