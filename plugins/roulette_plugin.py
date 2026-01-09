"""
俄罗斯轮盘赌插件 v2.0
触发命令：开枪、俄罗斯轮盘、🔫、轮盘
特殊子弹：玫瑰弹🌹、开花弹💥、空包弹💨、幸运弹🍀
技能：退弹（每小时1次）
规则：每轮6发，每人每轮只能开一枪
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.log import logger


# 子弹类型
class BulletType:
    NORMAL = "normal"      # 普通子弹 - 禁言5分钟
    ROSE = "rose"          # 玫瑰弹🌹 - 不禁言，送你一朵玫瑰
    BLOOM = "bloom"        # 开花弹💥 - 禁言翻倍10分钟
    BLANK = "blank"        # 空包弹💨 - 吓你一跳，不禁言
    LUCKY = "lucky"        # 幸运弹🍀 - 反弹给上一个开枪的人


# 禁言时长（秒）
BAN_DURATION = 5 * 60       # 普通：5分钟
BAN_DURATION_BLOOM = 10 * 60  # 开花弹：10分钟


class RouletteGame:
    """俄罗斯轮盘游戏管理器 v2.0"""
    
    def __init__(self, bullets: int = 6):
        self.bullets = bullets
        self.games: Dict[str, Dict] = {}  # 群游戏状态
        self.eject_cooldowns: Dict[str, datetime] = {}  # 退弹冷却 {group_user: last_eject_time}
        self.death_counts: Dict[str, int] = {}  # 死亡统计
        self.eject_cooldown_minutes = 60  # 退弹冷却时间
    
    def _get_key(self, group_id: str, user_id: str) -> str:
        return f"{group_id}_{user_id}"
    
    def get_or_create_game(self, group_id: str) -> Dict:
        """获取或创建群游戏状态"""
        if group_id not in self.games:
            self._reset_game(group_id)
        return self.games[group_id]
    
    def _reset_game(self, group_id: str):
        """重置游戏，随机生成子弹类型和位置"""
        # 随机子弹位置
        bullet_position = random.randint(1, self.bullets)
        
        # 随机子弹类型（权重）
        bullet_types = [
            (BulletType.NORMAL, 60),   # 60% 普通
            (BulletType.ROSE, 10),     # 10% 玫瑰弹
            (BulletType.BLOOM, 15),    # 15% 开花弹
            (BulletType.BLANK, 10),    # 10% 空包弹
            (BulletType.LUCKY, 5),     # 5% 幸运弹
        ]
        total = sum(w for _, w in bullet_types)
        rand = random.randint(1, total)
        current = 0
        bullet_type = BulletType.NORMAL
        for bt, weight in bullet_types:
            current += weight
            if rand <= current:
                bullet_type = bt
                break
        
        self.games[group_id] = {
            "current_position": 1,
            "bullet_position": bullet_position,
            "bullet_type": bullet_type,
            "played_users": set(),  # 本轮已开枪的用户
            "last_shooter": None,   # 上一个开枪的人（用于幸运弹反弹）
        }
    
    def can_play(self, group_id: str, user_id: str) -> tuple[bool, str]:
        """检查用户是否可以开枪"""
        game = self.get_or_create_game(group_id)
        if user_id in game["played_users"]:
            return False, "你这轮已经开过枪了喵，等下一轮吧~"
        return True, ""
    
    def pull_trigger(self, group_id: str, user_id: str) -> Dict:
        """
        开枪
        返回: {is_hit, bullet_type, current, bullet_pos, is_reflected, reflected_to}
        """
        game = self.get_or_create_game(group_id)
        
        # 记录玩家
        game["played_users"].add(user_id)
        last_shooter = game["last_shooter"]
        game["last_shooter"] = user_id
        
        current = game["current_position"]
        bullet_pos = game["bullet_position"]
        bullet_type = game["bullet_type"]
        
        result = {
            "is_hit": False,
            "bullet_type": bullet_type,
            "current": current,
            "bullet_pos": bullet_pos,
            "is_reflected": False,
            "reflected_to": None,
        }
        
        # 判断是否中枪
        if current == bullet_pos:
            result["is_hit"] = True
            
            # 幸运弹反弹逻辑
            if bullet_type == BulletType.LUCKY and last_shooter and last_shooter != user_id:
                result["is_reflected"] = True
                result["reflected_to"] = last_shooter
            
            # 记录死亡次数（空包弹和玫瑰弹不算）
            if bullet_type not in [BulletType.BLANK, BulletType.ROSE]:
                actual_victim = result["reflected_to"] if result["is_reflected"] else user_id
                key = self._get_key(group_id, actual_victim)
                self.death_counts[key] = self.death_counts.get(key, 0) + 1
            
            # 重置游戏
            self._reset_game(group_id)
        else:
            # 没中枪，位置+1
            game["current_position"] += 1
            # 转完一圈重置
            if game["current_position"] > self.bullets:
                self._reset_game(group_id)
        
        return result
    
    def eject_bullet(self, group_id: str, user_id: str) -> tuple[bool, str]:
        """
        退弹：重新随机子弹位置
        返回: (成功与否, 消息)
        """
        key = self._get_key(group_id, user_id)
        
        # 检查冷却
        if key in self.eject_cooldowns:
            last_eject = self.eject_cooldowns[key]
            cooldown_end = last_eject + timedelta(minutes=self.eject_cooldown_minutes)
            if datetime.now() < cooldown_end:
                remaining = int((cooldown_end - datetime.now()).total_seconds() / 60) + 1
                return False, f"退弹技能冷却中喵，还要等{remaining}分钟~"
        
        # 设置冷却
        self.eject_cooldowns[key] = datetime.now()
        
        # 重新随机子弹位置（不改变当前位置和子弹类型）
        game = self.get_or_create_game(group_id)
        old_pos = game["bullet_position"]
        new_pos = random.randint(1, self.bullets)
        game["bullet_position"] = new_pos
        
        return True, f"咔嚓~ 子弹被重新装填了喵！"
    
    def get_death_count(self, group_id: str, user_id: str) -> int:
        key = self._get_key(group_id, user_id)
        return self.death_counts.get(key, 0)
    
    def get_game_status(self, group_id: str) -> str:
        game = self.get_or_create_game(group_id)
        current = game["current_position"]
        remaining = self.bullets - current + 1
        played_count = len(game["played_users"])
        return f"当前第{current}发，还剩{remaining}发子弹，本轮已有{played_count}人开枪"


# 全局游戏实例
roulette = RouletteGame()

# 注册命令
roulette_cmd = on_command("开枪", aliases={"俄罗斯轮盘", "🔫", "轮盘"}, priority=5, block=True)
roulette_status = on_command("轮盘状态", aliases={"弹巢状态"}, priority=5, block=True)
eject_cmd = on_command("退弹", aliases={"换弹"}, priority=5, block=True)


# 子弹类型对应的消息
def get_hit_message(nickname: str, bullet_type: str, death_count: int, is_reflected: bool = False, reflected_nickname: str = None) -> str:
    """根据子弹类型生成中枪消息"""
    
    if bullet_type == BulletType.ROSE:
        return f"砰！{nickname} 中弹了...但是是玫瑰弹🌹！送你一朵玫瑰，不禁言喵~"
    
    elif bullet_type == BulletType.BLANK:
        return f"砰！！{nickname} 吓了一跳...原来是空包弹💨！虚惊一场喵~"
    
    elif bullet_type == BulletType.BLOOM:
        return f"砰！！！{nickname} 中了开花弹💥！禁言10分钟！这是ta第{death_count}次死亡喵..."
    
    elif bullet_type == BulletType.LUCKY:
        if is_reflected:
            return f"砰！{nickname} 中了幸运弹🍀！子弹反弹给了 {reflected_nickname}！禁言5分钟喵~"
        else:
            return f"砰！{nickname} 中了幸运弹🍀...但没有上一个开枪的人，只能自己承受了喵...禁言5分钟"
    
    else:  # NORMAL
        msgs = [
            f"砰！{nickname} 脑袋开花了，禁言5分钟喵...",
            f"砰！！{nickname} 倒下了，禁言5分钟喵~",
            f"砰！{nickname} 中弹身亡，禁言5分钟！这是ta第{death_count}次死亡喵",
        ]
        return random.choice(msgs)


# 存活消息
SURVIVE_MESSAGES = [
    "咔...{nickname} 活下来了喵！还剩{remaining}发子弹",
    "咔~ 空枪！{nickname} 命大喵，还有{remaining}发",
    "咔...没响！{nickname} 逃过一劫喵~ 剩余{remaining}发",
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
        
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        # 检查是否可以开枪
        can_play, reason = roulette.can_play(group_id, user_id)
        if not can_play:
            await roulette_cmd.finish(Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {reason}")
            ]))
            return
        
        # 开枪
        result = roulette.pull_trigger(group_id, user_id)
        
        if result["is_hit"]:
            # 中枪
            bullet_type = result["bullet_type"]
            death_count = roulette.get_death_count(group_id, user_id)
            
            # 确定实际受害者
            actual_victim_id = user_id
            reflected_nickname = None
            if result["is_reflected"] and result["reflected_to"]:
                actual_victim_id = result["reflected_to"]
                # 获取被反弹者的昵称
                try:
                    member_info = await bot.get_group_member_info(group_id=int(group_id), user_id=int(actual_victim_id))
                    reflected_nickname = member_info.get("card") or member_info.get("nickname") or actual_victim_id
                except:
                    reflected_nickname = actual_victim_id
                death_count = roulette.get_death_count(group_id, actual_victim_id)
            
            msg = get_hit_message(nickname, bullet_type, death_count, result["is_reflected"], reflected_nickname)
            
            # 尝试禁言（玫瑰弹和空包弹不禁言）
            if bullet_type not in [BulletType.ROSE, BulletType.BLANK]:
                ban_duration = BAN_DURATION_BLOOM if bullet_type == BulletType.BLOOM else BAN_DURATION
                try:
                    await bot.set_group_ban(
                        group_id=int(group_id),
                        user_id=int(actual_victim_id),
                        duration=ban_duration
                    )
                    logger.info(f"禁言成功: {actual_victim_id} {ban_duration//60}分钟")
                except Exception as e:
                    msg += "\n（但ta是管理员，小喵禁言不了喵 QAQ）"
                    logger.warning(f"禁言失败: {e}")
        else:
            # 存活
            game = roulette.get_or_create_game(group_id)
            remaining = roulette.bullets - game["current_position"] + 1
            msg = random.choice(SURVIVE_MESSAGES).format(nickname=nickname, remaining=remaining)
        
        await roulette_cmd.finish(Message([
            MessageSegment.at(user_id),
            MessageSegment.text(f" {msg}")
        ]))
        
        logger.info(f"俄罗斯轮盘: {nickname} {'中枪' if result['is_hit'] else '存活'}")
        
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


@eject_cmd.handle()
async def handle_eject(bot: Bot, event: Event):
    """退弹技能"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        success, msg = roulette.eject_bullet(group_id, user_id)
        
        await eject_cmd.finish(Message([
            MessageSegment.at(user_id),
            MessageSegment.text(f" {msg}")
        ]))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"退弹异常: {e}")
