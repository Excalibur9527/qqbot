"""
俄罗斯轮盘赌插件
触发命令：开枪、俄罗斯轮盘、🔫
防沉迷：每人每小时只能玩一次
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.log import logger


class RouletteGame:
    """俄罗斯轮盘游戏管理器"""
    
    def __init__(self, bullets: int = 6):
        self.bullets = bullets  # 左轮弹巢数
        self.games: Dict[str, Dict] = {}  # 群游戏状态
        self.cooldowns: Dict[str, datetime] = {}  # 玩家冷却时间 {group_user: last_play_time}
        self.death_counts: Dict[str, int] = {}  # 死亡统计 {group_user: count}
        self.cooldown_minutes = 60  # 冷却时间（分钟）
    
    def _get_key(self, group_id: str, user_id: str) -> str:
        """生成玩家唯一标识"""
        return f"{group_id}_{user_id}"
    
    def check_cooldown(self, group_id: str, user_id: str) -> Optional[int]:
        """
        检查冷却时间
        返回：None 表示可以玩，否则返回剩余冷却分钟数
        """
        key = self._get_key(group_id, user_id)
        if key not in self.cooldowns:
            return None
        
        last_play = self.cooldowns[key]
        cooldown_end = last_play + timedelta(minutes=self.cooldown_minutes)
        now = datetime.now()
        
        if now >= cooldown_end:
            return None
        
        remaining = (cooldown_end - now).total_seconds() / 60
        return int(remaining) + 1
    
    def set_cooldown(self, group_id: str, user_id: str):
        """设置冷却时间"""
        key = self._get_key(group_id, user_id)
        self.cooldowns[key] = datetime.now()
    
    def get_or_create_game(self, group_id: str) -> Dict:
        """获取或创建群游戏状态"""
        if group_id not in self.games:
            self.games[group_id] = {
                "current_position": 1,  # 当前弹巢位置
                "bullet_position": random.randint(1, self.bullets),  # 子弹位置
                "players": []  # 本轮参与的玩家
            }
        return self.games[group_id]
    
    def pull_trigger(self, group_id: str, user_id: str) -> tuple[bool, int, int]:
        """
        开枪
        返回：(是否中枪, 当前位置, 子弹位置)
        """
        game = self.get_or_create_game(group_id)
        
        # 记录玩家
        if user_id not in game["players"]:
            game["players"].append(user_id)
        
        current = game["current_position"]
        bullet = game["bullet_position"]
        
        # 判断是否中枪
        is_dead = (current == bullet)
        
        if is_dead:
            # 中枪，记录死亡次数，重置游戏
            key = self._get_key(group_id, user_id)
            self.death_counts[key] = self.death_counts.get(key, 0) + 1
            self.reset_game(group_id)
        else:
            # 没中枪，位置+1
            game["current_position"] += 1
            # 如果转完一圈还没死，重置
            if game["current_position"] > self.bullets:
                self.reset_game(group_id)
        
        return is_dead, current, bullet
    
    def reset_game(self, group_id: str):
        """重置游戏"""
        self.games[group_id] = {
            "current_position": 1,
            "bullet_position": random.randint(1, self.bullets),
            "players": []
        }
    
    def get_death_count(self, group_id: str, user_id: str) -> int:
        """获取玩家死亡次数"""
        key = self._get_key(group_id, user_id)
        return self.death_counts.get(key, 0)
    
    def get_game_status(self, group_id: str) -> str:
        """获取当前游戏状态"""
        game = self.get_or_create_game(group_id)
        current = game["current_position"]
        remaining = self.bullets - current + 1
        return f"当前第{current}发，还剩{remaining}个弹巢"


# 全局游戏实例
roulette = RouletteGame()

# 注册命令
roulette_cmd = on_command("开枪", aliases={"俄罗斯轮盘", "🔫", "轮盘"}, priority=5, block=True)
roulette_status = on_command("轮盘状态", aliases={"弹巢状态"}, priority=5, block=True)


# 禁言时长（秒）
BAN_DURATION = 5 * 60  # 5分钟

# 死亡回复模板（会被禁言）
DEATH_MESSAGES = [
    "砰！{nickname} 脑袋开花了，禁言5分钟喵...",
    "砰！！{nickname} 倒下了，闭嘴5分钟吧喵~",
    "砰！{nickname} 中弹身亡，禁言5分钟！这是ta第{count}次死亡喵",
    "砰！！！{nickname} 被爆头了喵！禁言5分钟，累计死亡{count}次",
    "砰！{nickname} 光荣牺牲，禁言5分钟喵~ 死亡次数+1，共{count}次",
]

# 死亡但禁言失败（管理员/群主）
DEATH_ADMIN_MESSAGES = [
    "砰！{nickname} 中弹了...但ta是管理员，小喵禁言不了喵 QAQ",
    "砰！{nickname} 倒下了...可惜是管理员，逃过禁言喵~",
    "砰！{nickname} 被爆头！但小喵权限不够禁言ta喵...",
]

# 存活回复模板
SURVIVE_MESSAGES = [
    "咔...{nickname} 活下来了喵！还剩{remaining}发",
    "咔~ 空枪！{nickname} 命大喵，还有{remaining}发",
    "咔...没响！{nickname} 逃过一劫喵~ 剩余{remaining}发",
    "咔~ {nickname} 今天运气不错喵！还剩{remaining}发",
]

# 冷却提示模板
COOLDOWN_MESSAGES = [
    "{nickname} 你刚玩过喵！还要等{minutes}分钟才能再玩",
    "{nickname} 防沉迷中喵~ {minutes}分钟后再来",
    "喵？{nickname} 你太上瘾了，休息{minutes}分钟吧",
]


@roulette_cmd.handle()
async def handle_roulette(bot: Bot, event: Event):
    """处理开枪命令"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await roulette_cmd.finish("这个游戏只能在群里玩喵~")
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        # 获取昵称
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        # 检查冷却
        remaining_minutes = roulette.check_cooldown(group_id, user_id)
        if remaining_minutes:
            msg = random.choice(COOLDOWN_MESSAGES).format(
                nickname=nickname,
                minutes=remaining_minutes
            )
            await roulette_cmd.finish(Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {msg}")
            ]))
            return
        
        # 设置冷却
        roulette.set_cooldown(group_id, user_id)
        
        # 开枪
        is_dead, current, bullet = roulette.pull_trigger(group_id, user_id)
        
        if is_dead:
            # 中枪，尝试禁言
            death_count = roulette.get_death_count(group_id, user_id)
            ban_success = False
            
            try:
                await bot.set_group_ban(
                    group_id=int(group_id),
                    user_id=int(user_id),
                    duration=BAN_DURATION
                )
                ban_success = True
                logger.info(f"禁言成功: {nickname}({user_id}) 5分钟")
            except Exception as e:
                logger.warning(f"禁言失败（可能是管理员）: {nickname}({user_id}), 错误: {e}")
            
            if ban_success:
                msg = random.choice(DEATH_MESSAGES).format(
                    nickname=nickname,
                    count=death_count
                )
            else:
                msg = random.choice(DEATH_ADMIN_MESSAGES).format(
                    nickname=nickname,
                    count=death_count
                )
        else:
            # 存活
            game = roulette.get_or_create_game(group_id)
            remaining = roulette.bullets - game["current_position"] + 1
            msg = random.choice(SURVIVE_MESSAGES).format(
                nickname=nickname,
                remaining=remaining
            )
        
        await roulette_cmd.finish(Message([
            MessageSegment.at(user_id),
            MessageSegment.text(f" {msg}")
        ]))
        
        logger.info(f"俄罗斯轮盘: {nickname} {'中枪' if is_dead else '存活'}, 位置{current}, 子弹在{bullet}")
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"俄罗斯轮盘异常: {e}")


@roulette_status.handle()
async def handle_status(bot: Bot, event: Event):
    """查看当前游戏状态"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        group_id = str(event.group_id)
        status = roulette.get_game_status(group_id)
        
        await roulette_status.finish(f"🔫 {status}喵~")
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"查看状态异常: {e}")
