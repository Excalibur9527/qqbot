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

# 数据迁移
def run_migration():
    """运行数据迁移"""
    try:
        from plugins.migrate_data import migrate_data
        migrate_data()
    except Exception as e:
        logger.error(f"数据迁移失败: {e}")

# 在NoneBot初始化后加载插件
def load_plugins():
    """加载插件"""
    try:
        # 先运行数据迁移
        run_migration()
        
        # 自定义插件（注意加载顺序）
        nonebot.load_plugin("plugins.test_plugin")
        nonebot.load_plugin("plugins.length_plugin")
        # woodfish_plugin 和 wordcloud_plugin 必须在 ai_chat_plugin 之前加载
        nonebot.load_plugin("plugins.woodfish_plugin")
        nonebot.load_plugin("plugins.wordcloud_plugin")
        nonebot.load_plugin("plugins.ai_chat_plugin")
        nonebot.load_plugin("plugins.pig_plugin")
        nonebot.load_plugin("plugins.roulette_plugin")
        nonebot.load_plugin("plugins.persona_plugin")
        nonebot.load_plugin("plugins.tarot_plugin")
        # 新增插件
        nonebot.load_plugin("plugins.fishing_plugin")
        nonebot.load_plugin("plugins.title_plugin")
        
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
