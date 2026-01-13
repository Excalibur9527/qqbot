"""
钓鱼插件
命令：/钓鱼、/打窝、/图鉴、/钓鱼榜、/图鉴榜
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.log import logger

from plugins.fishing_service import fishing_service, FishResult
from plugins.fish_data import get_fish_by_id, Rarity, ALL_FISH
from plugins.title_service import title_service
from plugins.unified_db import unified_db


# 注册命令
fish_cmd = on_command("钓鱼", priority=5, block=True)
bait_cmd = on_command("打窝", priority=5, block=True)
collection_cmd = on_command("图鉴", priority=5, block=True)
fish_rank_cmd = on_command("钓鱼榜", priority=5, block=True)
collection_rank_cmd = on_command("图鉴榜", priority=5, block=True)


def format_fish_result(result: FishResult) -> str:
    """格式化钓鱼结果"""
    if not result.success:
        return result.message
    
    fish = result.fish
    lines = []
    
    # 事件消息
    if result.event_message:
        lines.append(result.event_message)
        lines.append("")
    
    # 主要结果
    rarity_emoji = {
        Rarity.COMMON: "⚪",
        Rarity.RARE: "🔵",
        Rarity.EPIC: "🟣",
        Rarity.LEGENDARY: "🟡",
    }
    
    rarity_name = {
        Rarity.COMMON: "普通",
        Rarity.RARE: "稀有",
        Rarity.EPIC: "史诗",
        Rarity.LEGENDARY: "传说",
    }
    
    emoji = rarity_emoji.get(fish.rarity, "⚪")
    rarity = rarity_name.get(fish.rarity, "普通")
    
    # 特殊标记
    special = ""
    if fish.is_shiny:
        special = "✨闪光✨ "
    elif fish.is_dark:
        special = "🖤暗黑🖤 "
    
    lines.append(f"🎣 钓到了！")
    lines.append(f"{fish.emoji} {special}{fish.name}")
    lines.append(f"{emoji} {rarity} | 📏 {result.length}cm")
    
    if fish.description:
        lines.append(f"💬 {fish.description}")
    
    # 新图鉴/破纪录
    if result.is_new:
        lines.append("📖 【新图鉴解锁！】")
    if result.is_record:
        lines.append("🎉 【破纪录！】")
    
    # 额外的鱼
    if result.extra_fish:
        extra = result.extra_fish
        lines.append("")
        lines.append(f"🎁 意外收获！")
        lines.append(f"{extra.fish.emoji} {extra.fish.name} | 📏 {extra.length}cm")
        if extra.is_new:
            lines.append("📖 【新图鉴解锁！】")
    
    # 功德变化
    if result.merit_change != 0:
        if result.merit_change > 0:
            lines.append(f"功德 +{result.merit_change}")
        else:
            lines.append(f"功德 {result.merit_change}")
    
    return "\n".join(lines)


@fish_cmd.handle()
async def handle_fish(bot: Bot, event: Event):
    """处理钓鱼命令"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await fish_cmd.finish("请在群里钓鱼喵~")
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        # 执行钓鱼
        result = fishing_service.fish(group_id, user_id, nickname)
        
        # 格式化结果
        message = format_fish_result(result)
        
        # 检查头衔解锁
        new_titles = title_service.check_and_unlock(group_id, user_id)
        if new_titles:
            message += f"\n\n🏆 解锁新头衔：{', '.join(new_titles)}"
            # 设置QQ群头衔
            for title in new_titles:
                await title_service.set_qq_title(bot, group_id, user_id, title)
        
        await fish_cmd.finish(Message([
            MessageSegment.at(user_id),
            MessageSegment.text(f" {message}")
        ]))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"钓鱼异常: {e}")


@bait_cmd.handle()
async def handle_bait(bot: Bot, event: Event):
    """处理打窝命令"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await bait_cmd.finish("请在群里打窝喵~")
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        result = fishing_service.add_bait(group_id, user_id, nickname)
        
        await bait_cmd.finish(Message([
            MessageSegment.at(user_id),
            MessageSegment.text(f" {result.message}")
        ]))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"打窝异常: {e}")


@collection_cmd.handle()
async def handle_collection(bot: Bot, event: Event):
    """处理图鉴命令"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        # 获取命令参数
        msg = event.get_message()
        args = msg.extract_plain_text().strip()
        
        # 移除命令前缀（/图鉴 或 图鉴）
        if args.startswith("/图鉴"):
            args = args[3:].strip()
        elif args.startswith("图鉴"):
            args = args[2:].strip()
        
        if args:
            # 查询特定鱼
            fish = None
            for f in ALL_FISH:
                if f.name == args or f.id == args:
                    fish = f
                    break
            
            if not fish:
                await collection_cmd.finish(f"❌ 没有找到【{args}】这种鱼喵~")
                return
            
            # 获取用户记录
            record = unified_db.get_fish_record(group_id, user_id, fish.id)
            
            rarity_name = {
                Rarity.COMMON: "普通",
                Rarity.RARE: "稀有",
                Rarity.EPIC: "史诗",
                Rarity.LEGENDARY: "传说",
            }
            
            lines = [f"📖 {fish.emoji} {fish.name}"]
            lines.append(f"稀有度: {rarity_name.get(fish.rarity, '普通')}")
            
            if fish.is_shiny:
                lines.append("✨ 闪光鱼")
            if fish.is_dark:
                lines.append("🖤 暗黑鱼")
            
            lines.append(f"长度范围: {fish.min_length}-{fish.max_length}cm")
            
            # 活动时间
            if fish.active_start <= fish.active_end:
                lines.append(f"活动时间: {fish.active_start}:00-{fish.active_end}:00")
            else:
                lines.append(f"活动时间: {fish.active_start}:00-次日{fish.active_end}:00")
            
            if fish.description:
                lines.append(f"描述: {fish.description}")
            
            if record:
                lines.append(f"\n📊 你的记录:")
                lines.append(f"最大长度: {record.max_length}cm")
                lines.append(f"捕获次数: {record.catch_count}")
            else:
                lines.append(f"\n❓ 你还没有钓到过这种鱼")
            
            await collection_cmd.finish("\n".join(lines))
        else:
            # 显示图鉴总览
            stats = fishing_service.get_collection_stats(group_id, user_id)
            collection = unified_db.get_fish_collection(group_id, user_id)
            
            rarity_name = {
                Rarity.COMMON: "普通",
                Rarity.RARE: "稀有",
                Rarity.EPIC: "史诗",
                Rarity.LEGENDARY: "传说",
            }
            
            lines = ["📚 你的图鉴"]
            lines.append(f"进度: {stats['progress']}")
            lines.append("")
            
            # 按顺序显示各稀有度统计
            rarity_display = [
                (Rarity.COMMON, "普通"),
                (Rarity.RARE, "稀有"),
                (Rarity.EPIC, "史诗"),
                (Rarity.LEGENDARY, "传说"),
            ]
            
            for rarity, name in rarity_display:
                count = stats["by_rarity"].get(rarity, 0)
                total_rarity = len([f for f in ALL_FISH if f.rarity == rarity])
                lines.append(f"{name}: {count}/{total_rarity}")
            
            lines.append(f"暗黑鱼: {stats['dark']}/50")
            lines.append(f"闪光鱼: {stats['shiny']}/50")
            
            # 显示已钓到的鱼（最多显示前20条）
            if collection:
                lines.append("\n🐟 已钓到的鱼:")
                # 按特殊性和稀有度排序（闪光>传说>史诗>稀有>普通>暗黑）
                rarity_order = {
                    Rarity.LEGENDARY: 4,
                    Rarity.EPIC: 3,
                    Rarity.RARE: 2,
                    Rarity.COMMON: 1,
                }
                
                def sort_key(record):
                    fish = get_fish_by_id(record.fish_id)
                    if not fish:
                        return (0, 0, 0)
                    # 返回 (是否闪光, 稀有度值, 是否暗黑) 用于排序
                    return (
                        1 if fish.is_shiny else 0,
                        rarity_order.get(fish.rarity, 0),
                        1 if fish.is_dark else 0
                    )
                
                sorted_collection = sorted(collection, key=sort_key, reverse=True)
                
                display_count = min(20, len(sorted_collection))
                for i, record in enumerate(sorted_collection[:display_count]):
                    fish = get_fish_by_id(record.fish_id)
                    if fish:
                        special = ""
                        if fish.is_shiny:
                            special = "✨"
                        elif fish.is_dark:
                            special = "🖤"
                        lines.append(f"{special}{fish.emoji} {fish.name} (最大{record.max_length}cm)")
                
                if len(collection) > display_count:
                    lines.append(f"... 还有 {len(collection) - display_count} 种")
            
            lines.append("\n💡 使用 /图鉴 [鱼名] 查看详情")
            
            await collection_cmd.finish("\n".join(lines))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"图鉴异常: {e}")


@fish_rank_cmd.handle()
async def handle_fish_rank(bot: Bot, event: Event):
    """处理钓鱼榜命令"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        group_id = str(event.group_id)
        ranking = unified_db.get_fishing_ranking(group_id)
        
        if not ranking:
            await fish_rank_cmd.finish("还没人钓过鱼喵~")
            return
        
        lines = ["🎣 钓鱼排行榜 🎣\n"]
        medals = ["🥇", "🥈", "🥉"]
        
        for i, r in enumerate(ranking):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{medal} {r['nickname']}: {r['count']} 条")
        
        await fish_rank_cmd.finish("\n".join(lines))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"钓鱼榜异常: {e}")


@collection_rank_cmd.handle()
async def handle_collection_rank(bot: Bot, event: Event):
    """处理图鉴榜命令"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        group_id = str(event.group_id)
        ranking = unified_db.get_collection_ranking(group_id)
        
        if not ranking:
            await collection_rank_cmd.finish("还没人解锁图鉴喵~")
            return
        
        lines = ["📚 图鉴排行榜 📚\n"]
        medals = ["🥇", "🥈", "🥉"]
        
        for i, r in enumerate(ranking):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{medal} {r['nickname']}: {r['count']}/200")
        
        await collection_rank_cmd.finish("\n".join(lines))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"图鉴榜异常: {e}")
