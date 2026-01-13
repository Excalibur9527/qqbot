"""
钓鱼服务
核心钓鱼逻辑：概率计算、鱼类选择、长度生成
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from nonebot.log import logger

from plugins.fish_data import (
    Fish, Rarity, ALL_FISH, FISH_BY_ID, FISH_BY_RARITY,
    DARK_FISH_LIST, SHINY_FISH_LIST, NORMAL_FISH_LIST,
    get_fish_by_id, get_active_fish
)
from plugins.event_service import event_service
from plugins.unified_db import unified_db, UserData, FishRecord


@dataclass
class FishResult:
    """钓鱼结果"""
    success: bool
    fish: Optional[Fish] = None
    length: float = 0
    is_new: bool = False
    is_record: bool = False
    event_message: str = ""
    extra_fish: Optional['FishResult'] = None
    merit_change: int = 0
    message: str = ""


@dataclass
class BaitResult:
    """打窝结果"""
    success: bool
    bait_count: int = 0
    merit_cost: int = 0
    message: str = ""


class FishingService:
    """钓鱼服务"""
    
    # 基础概率配置
    BASE_PROBABILITIES = {
        Rarity.COMMON: 0.70,
        Rarity.RARE: 0.20,
        Rarity.EPIC: 0.08,
        Rarity.LEGENDARY: 0.02,
    }
    
    # 闪光基础概率
    BASE_SHINY_CHANCE = 0.05
    # 暗黑基础概率
    BASE_DARK_CHANCE = 0.10
    
    def fish(self, group_id: str, user_id: str, nickname: str) -> FishResult:
        """执行钓鱼"""
        # 获取用户数据
        user = unified_db.get_or_create_user(group_id, user_id, nickname)
        
        # 获取活跃效果
        effects = event_service.get_active_effects(group_id)
        
        # 检查是否无法钓鱼
        if effects.get("no_fishing"):
            return FishResult(False, message="⛈️ 暴风雨中无法钓鱼喵~")
        
        # 计算消耗
        cost = 1 * effects.get("cost_multiplier", 1)
        
        # 扣除功德（允许负数）
        unified_db.update_merit(group_id, user_id, nickname, -cost)
        
        # 检查是否下次必定失败
        if event_service.check_user_next_fail(group_id, user_id):
            return FishResult(False, merit_change=-cost, message="🌧️ 霉运缠身，钓鱼失败了喵...")
        
        # 触发随机事件
        event_result = event_service.trigger_random_event(group_id, user_id, nickname)
        event_message = event_result[1] if event_result else ""
        event = event_result[0] if event_result else None
        
        # 处理个人事件效果
        personal_effects = {}
        if event and not event.is_global():
            personal_effects = event.effects
            
            # 钓鱼失败事件
            if personal_effects.get("fail"):
                return FishResult(False, merit_change=-cost, event_message=event_message,
                                  message="😢 鱼跑了...")
        
        # 获取用户今日功德（重新查询，因为可能被事件改变）
        user = unified_db.get_or_create_user(group_id, user_id, nickname)
        today_merit = user.today_merit
        bait_count = user.bait_count
        
        # 负功德提示（仍然可以钓鱼，但只能钓暗黑鱼）
        if today_merit < 0 and not event_message:
            event_message = "⚠️ 功德为负，只能钓到暗黑鱼..."
        
        # 选择鱼
        fish = self._select_fish(today_merit, bait_count, effects, personal_effects)
        
        if not fish:
            return FishResult(False, merit_change=-cost, message="🎣 什么都没钓到喵...")
        
        # 生成长度
        length = self._generate_length(fish, effects, personal_effects)
        
        # 记录到图鉴
        record = unified_db.add_fish_record(group_id, user_id, fish.id, length)
        unified_db.increment_fish_count(group_id, user_id)
        
        result = FishResult(
            success=True,
            fish=fish,
            length=length,
            is_new=record.is_new,
            is_record=record.is_record,
            event_message=event_message,
            merit_change=-cost
        )
        
        # 处理双倍收获
        if effects.get("double") or personal_effects.get("extra_fish"):
            extra_fish = self._select_fish(today_merit, bait_count, effects, {})
            if extra_fish:
                extra_length = self._generate_length(extra_fish, effects, {})
                extra_record = unified_db.add_fish_record(group_id, user_id, extra_fish.id, extra_length)
                unified_db.increment_fish_count(group_id, user_id)
                result.extra_fish = FishResult(
                    success=True,
                    fish=extra_fish,
                    length=extra_length,
                    is_new=extra_record.is_new,
                    is_record=extra_record.is_record
                )
        
        # 处理功德雨效果
        if effects.get("merit_range"):
            bonus = random.randint(effects["merit_range"][0], effects["merit_range"][1])
            unified_db.update_merit(group_id, user_id, nickname, bonus)
            result.merit_change += bonus
        
        return result

    def _select_fish(self, today_merit: int, bait_count: int, 
                     effects: Dict, personal_effects: Dict) -> Optional[Fish]:
        """选择鱼"""
        hour = datetime.now().hour
        
        # 检查是否被诅咒或负功德（只能钓暗黑鱼）
        # 注意：负功德不会阻止钓鱼，只是限制只能钓到暗黑鱼
        dark_only = effects.get("dark_only") or today_merit < 0
        
        # 检查是否不能钓暗黑鱼
        no_dark = effects.get("no_dark")
        
        # 检查时空扭曲（可钓任意时间的鱼）
        all_time = effects.get("all_time")
        
        # 检查镜像世界
        mirror = effects.get("mirror")
        
        # 获取可钓的鱼
        if dark_only:
            available = [f for f in DARK_FISH_LIST if all_time or f.is_active(hour)]
        elif no_dark:
            available = [f for f in ALL_FISH if not f.is_dark and (all_time or f.is_active(hour))]
        else:
            available = [f for f in ALL_FISH if all_time or f.is_active(hour)]
        
        if not available:
            return None
        
        # 处理个人事件效果
        if personal_effects.get("guaranteed_rare"):
            # 必定稀有+
            available = [f for f in available if f.rarity in [Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY]]
            if not available:
                available = [f for f in ALL_FISH if f.rarity in [Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY]]
        
        if personal_effects.get("guaranteed_shiny"):
            # 必定闪光
            shiny_available = [f for f in available if f.is_shiny]
            if shiny_available:
                available = shiny_available
        
        # 计算概率
        probabilities = self._calculate_probabilities(today_merit, bait_count, effects)
        
        # 先决定稀有度
        rarity = self._select_rarity(probabilities)
        
        # 决定是否闪光
        shiny_chance = self.BASE_SHINY_CHANCE * effects.get("shiny_multiplier", 1)
        if today_merit >= 100:
            shiny_chance = 0.15 * effects.get("shiny_multiplier", 1)
        is_shiny = random.random() < shiny_chance
        
        # 决定是否暗黑
        dark_chance = self.BASE_DARK_CHANCE * effects.get("dark_multiplier", 1)
        is_dark = random.random() < dark_chance
        
        # 镜像世界效果
        if mirror:
            is_shiny, is_dark = is_dark, is_shiny
        
        # 筛选符合条件的鱼
        candidates = [f for f in available if f.rarity == rarity]
        
        if is_shiny and not dark_only:
            shiny_candidates = [f for f in candidates if f.is_shiny]
            if shiny_candidates:
                candidates = shiny_candidates
        elif is_dark and not no_dark:
            dark_candidates = [f for f in candidates if f.is_dark]
            if dark_candidates:
                candidates = dark_candidates
        else:
            normal_candidates = [f for f in candidates if not f.is_dark and not f.is_shiny]
            if normal_candidates:
                candidates = normal_candidates
        
        if not candidates:
            candidates = available
        
        return random.choice(candidates) if candidates else None
    
    def _select_rarity(self, probabilities: Dict[Rarity, float]) -> Rarity:
        """根据概率选择稀有度"""
        rand = random.random()
        cumulative = 0
        
        for rarity in [Rarity.LEGENDARY, Rarity.EPIC, Rarity.RARE, Rarity.COMMON]:
            cumulative += probabilities.get(rarity, 0)
            if rand < cumulative:
                return rarity
        
        return Rarity.COMMON
    
    def _calculate_probabilities(self, today_merit: int, bait_count: int, 
                                  effects: Dict) -> Dict[Rarity, float]:
        """计算各稀有度概率"""
        probs = dict(self.BASE_PROBABILITIES)
        
        # 打窝加成（每次+2%稀有概率，上限20%）
        bait_bonus = min(bait_count * 0.02, 0.20)
        
        # 应用加成
        rare_multiplier = effects.get("rare_multiplier", 1)
        legendary_multiplier = effects.get("legendary_multiplier", 1)
        
        probs[Rarity.RARE] = (probs[Rarity.RARE] + bait_bonus) * rare_multiplier
        probs[Rarity.EPIC] = probs[Rarity.EPIC] * rare_multiplier
        probs[Rarity.LEGENDARY] = probs[Rarity.LEGENDARY] * legendary_multiplier
        
        # 混沌效果
        if effects.get("chaos"):
            probs = {r: random.random() for r in Rarity}
        
        # 归一化
        total = sum(probs.values())
        if total > 0:
            probs = {r: p / total for r, p in probs.items()}
        
        return probs
    
    def _generate_length(self, fish: Fish, effects: Dict, personal_effects: Dict) -> float:
        """生成鱼的长度"""
        base_length = random.uniform(fish.min_length, fish.max_length)
        
        # 应用全局大小加成
        multiplier = effects.get("global_size_multiplier", 1)
        
        # 应用个人大小加成
        if personal_effects.get("size_multiplier"):
            multiplier *= personal_effects["size_multiplier"]
        
        length = base_length * multiplier
        return round(length, 1)
    
    def add_bait(self, group_id: str, user_id: str, nickname: str) -> BaitResult:
        """打窝"""
        user = unified_db.get_or_create_user(group_id, user_id, nickname)
        
        # 检查免费打窝
        is_free = event_service.check_free_bait(group_id, user_id)
        cost = 0 if is_free else 10
        
        if not is_free and user.total_merit < cost:
            return BaitResult(False, message="😿 功德不足，无法打窝喵~ (需要10功德)")
        
        # 扣除功德
        if cost > 0:
            unified_db.update_merit(group_id, user_id, nickname, -cost)
        
        # 增加打窝次数
        bait_count = unified_db.update_bait(group_id, user_id)
        
        bonus = min(bait_count * 2, 20)
        message = f"🪣 打窝成功！今日已打窝 {bait_count} 次\n稀有鱼概率 +{bonus}%"
        if is_free:
            message = "🎁 免费打窝！" + message
        
        return BaitResult(True, bait_count, cost, message)
    
    def get_collection_stats(self, group_id: str, user_id: str) -> Dict:
        """获取图鉴统计"""
        collection = unified_db.get_fish_collection(group_id, user_id)
        total = len(ALL_FISH)
        unlocked = len(collection)
        
        # 按稀有度统计
        by_rarity = {r: 0 for r in Rarity}
        for record in collection:
            fish = get_fish_by_id(record.fish_id)
            if fish:
                by_rarity[fish.rarity] += 1
        
        # 统计暗黑和闪光
        dark_count = sum(1 for r in collection if get_fish_by_id(r.fish_id) and get_fish_by_id(r.fish_id).is_dark)
        shiny_count = sum(1 for r in collection if get_fish_by_id(r.fish_id) and get_fish_by_id(r.fish_id).is_shiny)
        
        return {
            "total": total,
            "unlocked": unlocked,
            "by_rarity": by_rarity,
            "dark": dark_count,
            "shiny": shiny_count,
            "progress": f"{unlocked}/{total} ({unlocked*100//total}%)"
        }


# 全局实例
fishing_service = FishingService()
