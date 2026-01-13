"""
头衔插件
命令：/头衔、/头衔 [名称]、/头衔 无
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.log import logger

from plugins.title_service import title_service


# 注册命令
title_cmd = on_command("头衔", priority=5, block=True)
title_list_cmd = on_command("头衔列表", aliases={"头衔条件"}, priority=5, block=True)


@title_cmd.handle()
async def handle_title(bot: Bot, event: Event):
    """处理头衔命令"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await title_cmd.finish("请在群里使用喵~")
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        # 获取命令参数
        msg = event.get_message()
        args = msg.extract_plain_text().strip()
        
        # 移除命令前缀（/头衔 或 头衔）
        if args.startswith("/头衔"):
            args = args[3:].strip()
        elif args.startswith("头衔"):
            args = args[2:].strip()
        
        if not args:
            # 显示头衔列表
            message = title_service.format_titles_list(group_id, user_id)
            await title_cmd.finish(Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f"\n{message}")
            ]))
        elif args == "无" or args == "清除":
            # 清除头衔
            success, message = title_service.set_title(group_id, user_id, "")
            if success:
                await title_service.set_qq_title(bot, group_id, user_id, "")
            await title_cmd.finish(Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {message}")
            ]))
        elif args == "条件" or args == "列表":
            # 显示解锁条件
            message = title_service.get_title_requirements()
            await title_cmd.finish(message)
        else:
            # 切换头衔
            success, message = title_service.set_title(group_id, user_id, args)
            if success:
                await title_service.set_qq_title(bot, group_id, user_id, args)
            await title_cmd.finish(Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {message}")
            ]))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"头衔异常: {e}")


@title_list_cmd.handle()
async def handle_title_list(bot: Bot, event: Event):
    """处理头衔列表命令"""
    try:
        message = title_service.get_title_requirements()
        await title_list_cmd.finish(message)
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"头衔列表异常: {e}")
