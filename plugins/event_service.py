"""
事件服务
管理全局事件的触发、查询和清理
"""

import random
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from nonebot.log import logger

from plugins.event_data import (
    Event, EventType, ALL_EVENTS, GLOBAL_EVENTS, PERSONAL_EVENTS,
    GLOBAL_POSITIVE_EVENTS, GLOBAL_NEGATIVE_EVENTS, SPECIAL_EVENTS,
    PERSONAL_POSITIVE_EVENTS, PERSONAL_NEGATIVE_EVENTS,
    get_event_by_id
)
from plugins.unified_db import unified_db


class EventService:
    """事件服务"""
    
    # 用户诅咒计数
    user_curses: Dict[Tuple[str, str], int] = {}
    # 用户下次失败标记
    user_next_fail: Dict[Tuple[str, str], bool] = {}
    # 用户免费打窝标记
    user_free_bait: Dict[Tuple[str, str], bool] = {}
    
    def trigger_random_event(self, group_id: str, user_id: str, nickname: str, 
                             event_chance: float = 0.05) -> Optional[Tuple[Event, str]]:
        """触发随机事件，返回 (事件, 消息) 或 None"""
        if random.random() > event_chance:
            return None
        
        # 30%全局, 70%个人
        if random.random() < 0.3:
            event = self._select_global_event()
            if event:
                unified_db.add_global_event(group_id, event.id, event.duration, user_id)
                message = event.message.format(nickname=nickname)
                logger.info(f"触发全局事件: {event.name} by {nickname}")
                return event, message
        else:
            event = self._select_personal_event()
            if event:
                message = self._process_personal_event(event, group_id, user_id, nickname)
                logger.info(f"触发个人事件: {event.name} for {nickname}")
                return event, message
        return None
    
    def _select_global_event(self) -> Optional[Event]:
        """根据权重选择全局事件"""
        events = GLOBAL_POSITIVE_EVENTS + GLOBAL_NEGATIVE_EVENTS + SPECIAL_EVENTS
        if not events:
            return None
        total_weight = sum(e.weight for e in events)
        rand = random.uniform(0, total_weight)
        current = 0
        for event in events:
            current += event.weight
            if rand <= current:
                return event
        return events[0]
    
    def _select_personal_event(self) -> Optional[Event]:
        """根据权重选择个人事件"""
        events = PERSONAL_POSITIVE_EVENTS + PERSONAL_NEGATIVE_EVENTS
        if not events:
            return None
        total_weight = sum(e.weight for e in events)
        rand = random.uniform(0, total_weight)
        current = 0
        for event in events:
            current += event.weight
            if rand <= current:
                return event
        return events[0]

    def _process_personal_event(self, event: Event, group_id: str, user_id: str, nickname: str) -> str:
        """处理个人事件效果，返回消息"""
        effects = event.effects
        message = event.message
        
        # 处理功德变化
        if "merit_range" in effects:
            merit = random.randint(effects["merit_range"][0], effects["merit_range"][1])
            unified_db.update_merit(group_id, user_id, nickname, merit)
            message = message.format(nickname=nickname, merit=merit)
        elif "merit_loss" in effects:
            merit = effects["merit_loss"]
            unified_db.update_merit(group_id, user_id, nickname, -merit)
            message = message.format(nickname=nickname, merit=merit)
        elif "merit_loss_range" in effects:
            merit = random.randint(effects["merit_loss_range"][0], effects["merit_loss_range"][1])
            unified_db.update_merit(group_id, user_id, nickname, -merit)
            message = message.format(nickname=nickname, merit=merit)
        else:
            message = message.format(nickname=nickname)
        
        # 处理诅咒
        if "curse_count" in effects:
            key = (group_id, user_id)
            self.user_curses[key] = effects["curse_count"]
        
        # 处理下次失败
        if "next_fail" in effects:
            key = (group_id, user_id)
            self.user_next_fail[key] = True
        
        # 处理免费打窝
        if "free_bait" in effects:
            key = (group_id, user_id)
            self.user_free_bait[key] = True
        
        return message
    
    def get_active_events(self, group_id: str) -> List[Dict]:
        """获取当前活跃的全局事件"""
        return unified_db.get_active_events(group_id)
    
    def is_event_active(self, group_id: str, event_id: str) -> bool:
        """检查特定事件是否激活"""
        return unified_db.is_event_active(group_id, event_id)
    
    def get_active_effects(self, group_id: str) -> Dict[str, Any]:
        """获取当前所有活跃效果的汇总"""
        effects = {
            "dark_only": False,
            "no_dark": False,
            "no_fishing": False,
            "double": False,
            "all_time": False,
            "mirror": False,
            "chaos": False,
            "cost_multiplier": 1,
            "rare_multiplier": 1,
            "shiny_multiplier": 1,
            "dark_multiplier": 1,
            "legendary_multiplier": 1,
            "global_size_multiplier": 1,
            "merit_bonus": 0,
            "merit_range": None,
        }
        
        active_events = self.get_active_events(group_id)
        for event_data in active_events:
            event = get_event_by_id(event_data["event_type"])
            if not event:
                continue
            
            for key, value in event.effects.items():
                if key in effects:
                    if isinstance(effects[key], bool):
                        effects[key] = value
                    elif isinstance(effects[key], (int, float)):
                        if key.endswith("_multiplier"):
                            effects[key] *= value
                        else:
                            effects[key] += value if isinstance(value, (int, float)) else 0
                    elif effects[key] is None:
                        effects[key] = value
        
        return effects
    
    def check_user_curse(self, group_id: str, user_id: str) -> bool:
        """检查用户是否被诅咒，如果是则减少计数并返回True"""
        key = (group_id, user_id)
        if key in self.user_curses and self.user_curses[key] > 0:
            self.user_curses[key] -= 1
            if self.user_curses[key] <= 0:
                del self.user_curses[key]
            return True
        return False
    
    def check_user_next_fail(self, group_id: str, user_id: str) -> bool:
        """检查用户是否下次必定失败"""
        key = (group_id, user_id)
        if key in self.user_next_fail:
            del self.user_next_fail[key]
            return True
        return False
    
    def check_free_bait(self, group_id: str, user_id: str) -> bool:
        """检查用户是否有免费打窝"""
        key = (group_id, user_id)
        if key in self.user_free_bait:
            del self.user_free_bait[key]
            return True
        return False
    
    def cleanup_expired(self):
        """清理过期事件"""
        unified_db.cleanup_expired_events()


# 全局实例
event_service = EventService()
