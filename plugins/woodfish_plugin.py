"""
赛博敲木鱼插件
指令：敲木鱼、木鱼、/muyu
功能：累加功德值，有暴击和负面效果，每日排行榜
"""

import random
import sqlite3
import threading
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.log import logger


class WoodfishDatabase:
    """木鱼功德数据库"""
    
    def __init__(self, db_path: str = "data/woodfish.db"):
        self.db_path = db_path
        self._local = threading.local()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
    
    @property
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_tables(self):
        cursor = self._conn.cursor()
        # 总功德表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merit (
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                nickname TEXT,
                total_merit INTEGER DEFAULT 0,
                today_merit INTEGER DEFAULT 0,
                today_date TEXT,
                knock_count INTEGER DEFAULT 0,
                PRIMARY KEY (group_id, user_id)
            )
        """)
        self._conn.commit()
    
    def knock(self, group_id: str, user_id: str, nickname: str, delta: int) -> Tuple[int, int]:
        """
        敲木鱼，返回 (今日功德, 总功德)
        """
        cursor = self._conn.cursor()
        today = date.today().isoformat()
        
        # 查询现有记录
        cursor.execute("""
            SELECT total_merit, today_merit, today_date, knock_count 
            FROM merit WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        row = cursor.fetchone()
        
        if row:
            total = row["total_merit"]
            today_merit = row["today_merit"]
            last_date = row["today_date"]
            knock_count = row["knock_count"]
            
            # 如果是新的一天，重置今日功德
            if last_date != today:
                today_merit = 0
            
            total += delta
            today_merit += delta
            knock_count += 1
            
            cursor.execute("""
                UPDATE merit SET 
                    nickname = ?, total_merit = ?, today_merit = ?, 
                    today_date = ?, knock_count = ?
                WHERE group_id = ? AND user_id = ?
            """, (nickname, total, today_merit, today, knock_count, group_id, user_id))
        else:
            total = delta
            today_merit = delta
            cursor.execute("""
                INSERT INTO merit (group_id, user_id, nickname, total_merit, today_merit, today_date, knock_count)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (group_id, user_id, nickname, total, today_merit, today))
        
        self._conn.commit()
        return today_merit, total
    
    def get_today_ranking(self, group_id: str, limit: int = 10) -> List[Dict]:
        """获取今日功德排行榜"""
        cursor = self._conn.cursor()
        today = date.today().isoformat()
        cursor.execute("""
            SELECT nickname, user_id, today_merit 
            FROM merit 
            WHERE group_id = ? AND today_date = ? AND today_merit > 0
            ORDER BY today_merit DESC 
            LIMIT ?
        """, (group_id, today, limit))
        return [{"nickname": r["nickname"], "user_id": r["user_id"], "merit": r["today_merit"]} for r in cursor.fetchall()]
    
    def get_total_ranking(self, group_id: str, limit: int = 10) -> List[Dict]:
        """获取总功德排行榜"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT nickname, user_id, total_merit 
            FROM merit 
            WHERE group_id = ? AND total_merit > 0
            ORDER BY total_merit DESC 
            LIMIT ?
        """, (group_id, limit))
        return [{"nickname": r["nickname"], "user_id": r["user_id"], "merit": r["total_merit"]} for r in cursor.fetchall()]
    
    def deduct_merit(self, group_id: str, user_id: str, nickname: str, amount: int = 10) -> Tuple[int, int]:
        """
        扣减功德（用于惩罚），返回 (今日功德, 总功德)
        """
        return self.knock(group_id, user_id, nickname, -amount)


# 全局实例
woodfish_db = WoodfishDatabase()

# 敲木鱼结果配置 (delta, weight, message)
KNOCK_RESULTS = [
    (1, 50, "🪵 咚~ 功德 +1"),
    (2, 20, "🪵 咚咚~ 功德 +2"),
    (5, 10, "🪵 咚咚咚~ 功德 +5"),
    (10, 8, "✨ 木鱼发光了！功德 +10"),
    (50, 5, "🌟 佛祖显灵！功德 +50"),
    (100, 3, "💫 暴击！！功德 +100！！"),
    (233, 1, "🎉 超级暴击！功德 +233！！！"),
    (-5, 2, "💥 木鱼敲裂了...功德 -5"),
    (-10, 1, "😱 木鱼碎了！功德 -10"),
]

def get_knock_result() -> Tuple[int, str]:
    """根据权重随机获取敲木鱼结果"""
    total_weight = sum(r[1] for r in KNOCK_RESULTS)
    rand = random.randint(1, total_weight)
    current = 0
    for delta, weight, msg in KNOCK_RESULTS:
        current += weight
        if rand <= current:
            return delta, msg
    return 1, "🪵 咚~ 功德 +1"


# 注册命令
knock_cmd = on_command("敲木鱼", aliases={"木鱼", "muyu", "敲"}, priority=5, block=True)
merit_rank_cmd = on_command("功德榜", aliases={"功德排行", "今日功德榜"}, priority=5, block=True)
total_merit_cmd = on_command("总功德榜", aliases={"功德总榜"}, priority=5, block=True)


@knock_cmd.handle()
async def handle_knock(bot: Bot, event: Event):
    """敲木鱼"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await knock_cmd.finish("请在群里敲木鱼喵~")
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        # 敲木鱼
        delta, msg = get_knock_result()
        today_merit, total_merit = woodfish_db.knock(group_id, user_id, nickname, delta)
        
        result = f"{msg}\n今日功德: {today_merit} | 总功德: {total_merit}"
        
        await knock_cmd.finish(Message([
            MessageSegment.at(user_id),
            MessageSegment.text(f" {result}")
        ]))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"敲木鱼异常: {e}")


@merit_rank_cmd.handle()
async def handle_merit_rank(bot: Bot, event: Event):
    """今日功德排行榜"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        group_id = str(event.group_id)
        ranking = woodfish_db.get_today_ranking(group_id)
        
        if not ranking:
            await merit_rank_cmd.finish("今天还没人敲木鱼喵~")
            return
        
        lines = ["📿 今日功德排行榜 📿\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, r in enumerate(ranking):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{medal} {r['nickname']}: {r['merit']} 功德")
        
        await merit_rank_cmd.finish("\n".join(lines))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"功德榜异常: {e}")


@total_merit_cmd.handle()
async def handle_total_merit(bot: Bot, event: Event):
    """总功德排行榜"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return
        
        group_id = str(event.group_id)
        ranking = woodfish_db.get_total_ranking(group_id)
        
        if not ranking:
            await total_merit_cmd.finish("还没人积累功德喵~")
            return
        
        lines = ["🏆 总功德排行榜 🏆\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, r in enumerate(ranking):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{medal} {r['nickname']}: {r['merit']} 功德")
        
        await total_merit_cmd.finish("\n".join(lines))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"总功德榜异常: {e}")
