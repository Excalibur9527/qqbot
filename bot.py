#!/usr/bin/env python3
"""
NoneBot2 QQ机器人主程序
基于NapCat + OneBot协议
"""

import nonebot
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    GroupMessageEvent,
    Message,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.params import CommandArg, ArgPlainText
from nonebot.rule import to_me
from nonebot.log import logger

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 配置NoneBot - 使用默认驱动（会根据依赖自动选择支持WebSocket的驱动）
nonebot.init()

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 在NoneBot初始化后加载插件
def load_plugins():
    """加载插件"""
    try:
        # 自定义插件
        nonebot.load_plugin("plugins.test_plugin")
        nonebot.load_plugin("plugins.length_plugin")
        nonebot.load_plugin("plugins.ai_chat_plugin")
        nonebot.load_plugin("plugins.joke_plugin")
        nonebot.load_plugin("plugins.pig_plugin")
        nonebot.load_plugin("plugins.roulette_plugin")
        nonebot.load_plugin("plugins.woodfish_plugin")
        nonebot.load_plugin("plugins.persona_plugin")
        nonebot.load_plugin("plugins.tarot_plugin")
        
        logger.info("插件加载完成")
    except Exception as e:
        logger.error(f"插件加载失败: {e}")
        # 不抛出异常，让其他插件继续运行
        # raise 

# 加载插件
load_plugins()

if __name__ == "__main__":
    logger.info("启动NoneBot2 QQ机器人...")
    nonebot.run()
