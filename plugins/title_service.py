"""
头衔服务
管理头衔的解锁、查询和设置
"""

from typing import Dict, List, Optional, Tuple
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot

from plugins.unified_db import unified_db, UserData


class TitleService:
    """头衔服务"""
    
    # 功德头衔配置
    MERIT_TITLES = {
        "today": [
            (100, "功德"),
            (500, "电子居士"),
            (1000, "量子菩萨"),
        ],
        "total": [
            (1000, "敲鱼居士"),
            (2000, "赛博罗汉"),
            (5000, "机械飞升"),
            (10000, "赛博如来"),
        ]
    }
    
    # 钓鱼头衔配置
    FISH_TITLES = {
        50: "钓鱼佬",
        200: "赛博鱼王",
    }
    
    # 所有头衔列表
    ALL_TITLES = (
        [t[1] for t in MERIT_TITLES["today"]] +
        [t[1] for t in MERIT_TITLES["total"]] +
        list(FISH_TITLES.values())
    )
    
    def check_and_unlock(self, group_id: str, user_id: str) -> List[str]:
        """检查并解锁新头衔，返回新解锁的头衔列表"""
        user = unified_db.get_user(group_id, user_id)
        if not user:
            return []
        
        new_titles = []
        
        # 检查今日功德头衔
        for threshold, title in self.MERIT_TITLES["today"]:
            if user.today_merit >= threshold:
                if unified_db.unlock_title(group_id, user_id, title):
                    new_titles.append(title)
                    logger.info(f"解锁头衔: {user.nickname}({user_id}) -> {title}")
        
        # 检查总功德头衔
        for threshold, title in self.MERIT_TITLES["total"]:
            if user.total_merit >= threshold:
                if unified_db.unlock_title(group_id, user_id, title):
                    new_titles.append(title)
                    logger.info(f"解锁头衔: {user.nickname}({user_id}) -> {title}")
        
        # 检查钓鱼头衔
        collection_count = unified_db.get_collection_count(group_id, user_id)
        for threshold, title in self.FISH_TITLES.items():
            if collection_count >= threshold:
                if unified_db.unlock_title(group_id, user_id, title):
                    new_titles.append(title)
                    logger.info(f"解锁头衔: {user.nickname}({user_id}) -> {title}")
        
        return new_titles
    
    def get_user_titles(self, group_id: str, user_id: str) -> List[str]:
        """获取用户已解锁的头衔"""
        return unified_db.get_user_titles(group_id, user_id)
    
    def get_current_title(self, group_id: str, user_id: str) -> str:
        """获取用户当前佩戴的头衔"""
        return unified_db.get_current_title(group_id, user_id)
    
    def set_title(self, group_id: str, user_id: str, title: str) -> Tuple[bool, str]:
        """
        设置用户头衔
        返回: (是否成功, 消息)
        """
        if title and title not in self.ALL_TITLES:
            return False, f"❌ 不存在的头衔: {title}"
        
        titles = self.get_user_titles(group_id, user_id)
        
        if title and title not in titles:
            return False, f"❌ 你还没有解锁【{title}】头衔喵~"
        
        success = unified_db.set_current_title(group_id, user_id, title)
        
        if success:
            if title:
                return True, f"✅ 已切换头衔为【{title}】"
            else:
                return True, "✅ 已清除头衔"
        else:
            return False, "❌ 设置头衔失败"
    
    async def set_qq_title(self, bot: Bot, group_id: str, user_id: str, title: str) -> bool:
        """调用QQ API设置群头衔"""
        try:
            await bot.call_api(
                "set_group_special_title",
                group_id=int(group_id),
                user_id=int(user_id),
                special_title=title or "",
                duration=-1
            )
            logger.info(f"设置群头衔成功: {user_id} -> {title}")
            return True
        except Exception as e:
            logger.error(f"设置群头衔失败: {e}")
            return False
    
    def format_titles_list(self, group_id: str, user_id: str) -> str:
        """格式化头衔列表显示"""
        titles = self.get_user_titles(group_id, user_id)
        current = self.get_current_title(group_id, user_id)
        
        if not titles:
            return "📜 你还没有解锁任何头衔喵~\n\n敲木鱼或钓鱼来解锁头衔吧！"
        
        lines = ["📜 你的头衔列表：\n"]
        
        for title in titles:
            if title == current:
                lines.append(f"  👑 【{title}】 (当前)")
            else:
                lines.append(f"  📿 {title}")
        
        lines.append("\n💡 使用 /头衔 [名称] 切换头衔")
        lines.append("💡 使用 /头衔 无 清除头衔")
        
        return "\n".join(lines)
    
    def get_title_requirements(self) -> str:
        """获取头衔解锁条件说明"""
        lines = ["🏆 头衔解锁条件：\n"]
        
        lines.append("【功德成就】")
        for threshold, title in self.MERIT_TITLES["today"]:
            lines.append(f"  单日功德 {threshold}+ → {title}")
        for threshold, title in self.MERIT_TITLES["total"]:
            lines.append(f"  总功德 {threshold}+ → {title}")
        
        lines.append("\n【钓鱼成就】")
        for threshold, title in self.FISH_TITLES.items():
            lines.append(f"  解锁 {threshold} 种鱼 → {title}")
        
        return "\n".join(lines)


# 全局实例
title_service = TitleService()
