"""
统一用户数据库模块
整合功德、长度、钓鱼、头衔、人设等数据到单一数据库
"""

import sqlite3
import threading
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
from dataclasses import dataclass, asdict
from nonebot.log import logger


@dataclass
class UserData:
    """用户完整数据"""
    group_id: str
    user_id: str
    nickname: str = ""
    # 功德
    total_merit: int = 0
    today_merit: int = 0
    today_date: str = ""
    knock_count: int = 0
    # 长度
    today_length: Optional[int] = None
    length_date: str = ""
    # 钓鱼
    fish_count: int = 0
    bait_count: int = 0
    bait_date: str = ""
    # 头衔
    unlocked_titles: List[str] = None
    current_title: str = ""
    # 人设
    profile: str = ""
    tags: List[str] = None
    message_count: int = 0
    
    def __post_init__(self):
        if self.unlocked_titles is None:
            self.unlocked_titles = []
        if self.tags is None:
            self.tags = []


@dataclass
class FishRecord:
    """钓鱼记录"""
    fish_id: str
    max_length: float
    catch_count: int
    first_catch: str
    is_new: bool = False
    is_record: bool = False


class UnifiedDatabase:
    """统一用户数据库管理器"""
    
    def __init__(self, db_path: str = "data/unified_data.db"):
        self.db_path = db_path
        self._local = threading.local()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
        logger.info(f"UnifiedDatabase 初始化完成: {db_path}")
    
    @property
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_tables(self):
        cursor = self._conn.cursor()
        
        # 统一用户数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_data (
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                nickname TEXT DEFAULT '',
                -- 功德相关
                total_merit INTEGER DEFAULT 0,
                today_merit INTEGER DEFAULT 0,
                today_date TEXT DEFAULT '',
                knock_count INTEGER DEFAULT 0,
                -- 长度相关
                today_length INTEGER,
                length_date TEXT DEFAULT '',
                -- 钓鱼相关
                fish_count INTEGER DEFAULT 0,
                bait_count INTEGER DEFAULT 0,
                bait_date TEXT DEFAULT '',
                -- 头衔相关
                unlocked_titles TEXT DEFAULT '[]',
                current_title TEXT DEFAULT '',
                -- 人设相关
                profile TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                message_count INTEGER DEFAULT 0,
                -- 时间戳
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id)
            )
        """)
        
        # 鱼类图鉴表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fish_collection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                fish_id TEXT NOT NULL,
                max_length REAL DEFAULT 0,
                catch_count INTEGER DEFAULT 1,
                first_catch DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, user_id, fish_id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fish_collection 
            ON fish_collection(group_id, user_id)
        """)
        
        # 全局事件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                expire_time DATETIME NOT NULL,
                triggered_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_global_events 
            ON global_events(group_id, expire_time)
        """)
        
        # 对话历史表（从 profile_db 迁移）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_history 
            ON conversation_history(group_id, user_id)
        """)
        
        # 消息缓冲表（用于人设分析）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 用户记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                event TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self._conn.commit()

    # ========== 用户数据操作 ==========
    
    def _check_daily_reset(self, row: sqlite3.Row) -> Tuple[int, int, int]:
        """检查是否需要每日重置，返回 (today_merit, bait_count, today_length)"""
        today = date.today().isoformat()
        today_merit = row["today_merit"] if row["today_date"] == today else 0
        bait_count = row["bait_count"] if row["bait_date"] == today else 0
        today_length = row["today_length"] if row["length_date"] == today else None
        return today_merit, bait_count, today_length
    
    def get_user(self, group_id: str, user_id: str) -> Optional[UserData]:
        """获取用户完整数据"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM user_data WHERE group_id = ? AND user_id = ?", 
                       (group_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        today_merit, bait_count, today_length = self._check_daily_reset(row)
        
        try:
            unlocked_titles = json.loads(row["unlocked_titles"] or "[]")
        except:
            unlocked_titles = []
        
        try:
            tags = json.loads(row["tags"] or "[]")
        except:
            tags = []
        
        return UserData(
            group_id=row["group_id"],
            user_id=row["user_id"],
            nickname=row["nickname"] or "",
            total_merit=row["total_merit"],
            today_merit=today_merit,
            today_date=row["today_date"],
            knock_count=row["knock_count"],
            today_length=today_length,
            length_date=row["length_date"],
            fish_count=row["fish_count"],
            bait_count=bait_count,
            bait_date=row["bait_date"],
            unlocked_titles=unlocked_titles,
            current_title=row["current_title"] or "",
            profile=row["profile"] or "",
            tags=tags,
            message_count=row["message_count"]
        )
    
    def get_or_create_user(self, group_id: str, user_id: str, nickname: str = "") -> UserData:
        """获取或创建用户数据"""
        user = self.get_user(group_id, user_id)
        if user:
            if nickname and nickname != user.nickname:
                self.update_nickname(group_id, user_id, nickname)
                user.nickname = nickname
            return user
        
        # 创建新用户
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO user_data (group_id, user_id, nickname)
            VALUES (?, ?, ?)
        """, (group_id, user_id, nickname))
        self._conn.commit()
        
        return UserData(group_id=group_id, user_id=user_id, nickname=nickname)
    
    def update_nickname(self, group_id: str, user_id: str, nickname: str):
        """更新用户昵称"""
        cursor = self._conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO user_data (group_id, user_id, nickname, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(group_id, user_id) DO UPDATE SET
                nickname = excluded.nickname,
                updated_at = excluded.updated_at
        """, (group_id, user_id, nickname, now))
        self._conn.commit()
    
    # ========== 功德操作 ==========
    
    def update_merit(self, group_id: str, user_id: str, nickname: str, delta: int) -> Tuple[int, int]:
        """
        更新功德，返回 (今日功德, 总功德)
        """
        cursor = self._conn.cursor()
        today = date.today().isoformat()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("SELECT * FROM user_data WHERE group_id = ? AND user_id = ?",
                       (group_id, user_id))
        row = cursor.fetchone()
        
        if row:
            total = row["total_merit"]
            today_merit = row["today_merit"] if row["today_date"] == today else 0
            knock_count = row["knock_count"]
            
            total += delta
            today_merit += delta
            knock_count += 1
            
            cursor.execute("""
                UPDATE user_data SET 
                    nickname = ?, total_merit = ?, today_merit = ?,
                    today_date = ?, knock_count = ?, updated_at = ?
                WHERE group_id = ? AND user_id = ?
            """, (nickname, total, today_merit, today, knock_count, now, group_id, user_id))
        else:
            total = delta
            today_merit = delta
            cursor.execute("""
                INSERT INTO user_data (group_id, user_id, nickname, total_merit, 
                    today_merit, today_date, knock_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (group_id, user_id, nickname, total, today_merit, today, now))
        
        self._conn.commit()
        return today_merit, total
    
    def deduct_merit(self, group_id: str, user_id: str, nickname: str, amount: int = 10) -> Tuple[int, int]:
        """扣减功德"""
        return self.update_merit(group_id, user_id, nickname, -amount)
    
    # ========== 长度操作 ==========
    
    def update_length(self, group_id: str, user_id: str, length: int) -> int:
        """更新今日长度，返回长度值"""
        cursor = self._conn.cursor()
        today = date.today().isoformat()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO user_data (group_id, user_id, today_length, length_date, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(group_id, user_id) DO UPDATE SET
                today_length = excluded.today_length,
                length_date = excluded.length_date,
                updated_at = excluded.updated_at
        """, (group_id, user_id, length, today, now))
        self._conn.commit()
        return length
    
    def get_length(self, group_id: str, user_id: str) -> Optional[int]:
        """获取今日长度，如果不是今天的数据返回 None"""
        user = self.get_user(group_id, user_id)
        if user:
            return user.today_length
        return None
    
    def get_length_ranking(self, group_id: str, limit: int = 10) -> List[Dict]:
        """获取今日长度排行榜"""
        cursor = self._conn.cursor()
        today = date.today().isoformat()
        
        cursor.execute("""
            SELECT nickname, user_id, today_length
            FROM user_data 
            WHERE group_id = ? AND length_date = ? AND today_length IS NOT NULL
            ORDER BY today_length DESC 
            LIMIT ?
        """, (group_id, today, limit))
        
        return [{"nickname": r["nickname"], "user_id": r["user_id"], "length": r["today_length"]} 
                for r in cursor.fetchall()]
    
    def get_merit_ranking(self, group_id: str, ranking_type: str = "today", limit: int = 10) -> List[Dict]:
        """获取功德排行榜"""
        cursor = self._conn.cursor()
        today = date.today().isoformat()
        
        if ranking_type == "today":
            cursor.execute("""
                SELECT nickname, user_id, today_merit as merit
                FROM user_data 
                WHERE group_id = ? AND today_date = ?
                ORDER BY today_merit DESC 
                LIMIT ?
            """, (group_id, today, limit))
        else:
            cursor.execute("""
                SELECT nickname, user_id, total_merit as merit
                FROM user_data 
                WHERE group_id = ?
                ORDER BY total_merit DESC 
                LIMIT ?
            """, (group_id, limit))
        
        return [{"nickname": r["nickname"], "user_id": r["user_id"], "merit": r["merit"]} 
                for r in cursor.fetchall()]

    # ========== 钓鱼操作 ==========
    
    def update_bait(self, group_id: str, user_id: str) -> int:
        """打窝，返回今日打窝次数"""
        cursor = self._conn.cursor()
        today = date.today().isoformat()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("SELECT bait_count, bait_date FROM user_data WHERE group_id = ? AND user_id = ?",
                       (group_id, user_id))
        row = cursor.fetchone()
        
        if row:
            bait_count = row["bait_count"] if row["bait_date"] == today else 0
            bait_count += 1
            cursor.execute("""
                UPDATE user_data SET bait_count = ?, bait_date = ?, updated_at = ?
                WHERE group_id = ? AND user_id = ?
            """, (bait_count, today, now, group_id, user_id))
        else:
            bait_count = 1
            cursor.execute("""
                INSERT INTO user_data (group_id, user_id, bait_count, bait_date, updated_at)
                VALUES (?, ?, 1, ?, ?)
            """, (group_id, user_id, today, now))
        
        self._conn.commit()
        return bait_count
    
    def increment_fish_count(self, group_id: str, user_id: str) -> int:
        """增加钓鱼次数，返回总次数"""
        cursor = self._conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE user_data SET fish_count = fish_count + 1, updated_at = ?
            WHERE group_id = ? AND user_id = ?
        """, (now, group_id, user_id))
        
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO user_data (group_id, user_id, fish_count, updated_at)
                VALUES (?, ?, 1, ?)
            """, (group_id, user_id, now))
            return 1
        
        cursor.execute("SELECT fish_count FROM user_data WHERE group_id = ? AND user_id = ?",
                       (group_id, user_id))
        self._conn.commit()
        return cursor.fetchone()["fish_count"]
    
    # ========== 图鉴操作 ==========
    
    def add_fish_record(self, group_id: str, user_id: str, fish_id: str, length: float) -> FishRecord:
        """添加钓鱼记录，返回记录信息（包含是否新图鉴、是否破纪录）"""
        cursor = self._conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            SELECT max_length, catch_count, first_catch 
            FROM fish_collection 
            WHERE group_id = ? AND user_id = ? AND fish_id = ?
        """, (group_id, user_id, fish_id))
        row = cursor.fetchone()
        
        is_new = row is None
        is_record = False
        
        if row:
            old_max = row["max_length"]
            catch_count = row["catch_count"] + 1
            is_record = length > old_max
            new_max = max(old_max, length)
            
            cursor.execute("""
                UPDATE fish_collection 
                SET max_length = ?, catch_count = ?
                WHERE group_id = ? AND user_id = ? AND fish_id = ?
            """, (new_max, catch_count, group_id, user_id, fish_id))
            first_catch = row["first_catch"]
        else:
            cursor.execute("""
                INSERT INTO fish_collection (group_id, user_id, fish_id, max_length, catch_count, first_catch)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (group_id, user_id, fish_id, length, now))
            catch_count = 1
            first_catch = now
            is_record = True
        
        self._conn.commit()
        
        return FishRecord(
            fish_id=fish_id,
            max_length=length if is_record else (row["max_length"] if row else length),
            catch_count=catch_count,
            first_catch=first_catch,
            is_new=is_new,
            is_record=is_record
        )
    
    def get_fish_collection(self, group_id: str, user_id: str) -> List[FishRecord]:
        """获取用户图鉴"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT fish_id, max_length, catch_count, first_catch
            FROM fish_collection
            WHERE group_id = ? AND user_id = ?
            ORDER BY first_catch DESC
        """, (group_id, user_id))
        
        return [FishRecord(
            fish_id=r["fish_id"],
            max_length=r["max_length"],
            catch_count=r["catch_count"],
            first_catch=r["first_catch"]
        ) for r in cursor.fetchall()]
    
    def get_collection_count(self, group_id: str, user_id: str) -> int:
        """获取图鉴解锁数量"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM fish_collection
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        return cursor.fetchone()["count"]
    
    def get_fish_record(self, group_id: str, user_id: str, fish_id: str) -> Optional[FishRecord]:
        """获取单鱼记录"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT fish_id, max_length, catch_count, first_catch
            FROM fish_collection
            WHERE group_id = ? AND user_id = ? AND fish_id = ?
        """, (group_id, user_id, fish_id))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return FishRecord(
            fish_id=row["fish_id"],
            max_length=row["max_length"],
            catch_count=row["catch_count"],
            first_catch=row["first_catch"]
        )
    
    def get_fishing_ranking(self, group_id: str, limit: int = 10) -> List[Dict]:
        """获取钓鱼数量排行"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT nickname, user_id, fish_count
            FROM user_data 
            WHERE group_id = ? AND fish_count > 0
            ORDER BY fish_count DESC 
            LIMIT ?
        """, (group_id, limit))
        return [{"nickname": r["nickname"], "user_id": r["user_id"], "count": r["fish_count"]} 
                for r in cursor.fetchall()]
    
    def get_collection_ranking(self, group_id: str, limit: int = 10) -> List[Dict]:
        """获取图鉴解锁数量排行"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT u.nickname, u.user_id, COUNT(f.fish_id) as count
            FROM user_data u
            LEFT JOIN fish_collection f ON u.group_id = f.group_id AND u.user_id = f.user_id
            WHERE u.group_id = ?
            GROUP BY u.group_id, u.user_id
            HAVING count > 0
            ORDER BY count DESC
            LIMIT ?
        """, (group_id, limit))
        return [{"nickname": r["nickname"], "user_id": r["user_id"], "count": r["count"]} 
                for r in cursor.fetchall()]

    # ========== 头衔操作 ==========
    
    def unlock_title(self, group_id: str, user_id: str, title: str) -> bool:
        """解锁头衔，返回是否为新解锁"""
        cursor = self._conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("SELECT unlocked_titles FROM user_data WHERE group_id = ? AND user_id = ?",
                       (group_id, user_id))
        row = cursor.fetchone()
        
        if row:
            try:
                titles = json.loads(row["unlocked_titles"] or "[]")
            except:
                titles = []
            
            if title in titles:
                return False
            
            titles.append(title)
            cursor.execute("""
                UPDATE user_data SET unlocked_titles = ?, updated_at = ?
                WHERE group_id = ? AND user_id = ?
            """, (json.dumps(titles, ensure_ascii=False), now, group_id, user_id))
        else:
            cursor.execute("""
                INSERT INTO user_data (group_id, user_id, unlocked_titles, updated_at)
                VALUES (?, ?, ?, ?)
            """, (group_id, user_id, json.dumps([title], ensure_ascii=False), now))
        
        self._conn.commit()
        return True
    
    def get_user_titles(self, group_id: str, user_id: str) -> List[str]:
        """获取用户已解锁头衔"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT unlocked_titles FROM user_data WHERE group_id = ? AND user_id = ?",
                       (group_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            return []
        
        try:
            return json.loads(row["unlocked_titles"] or "[]")
        except:
            return []
    
    def set_current_title(self, group_id: str, user_id: str, title: str) -> bool:
        """设置当前佩戴头衔"""
        cursor = self._conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查是否已解锁
        titles = self.get_user_titles(group_id, user_id)
        if title and title not in titles:
            return False
        
        cursor.execute("""
            UPDATE user_data SET current_title = ?, updated_at = ?
            WHERE group_id = ? AND user_id = ?
        """, (title, now, group_id, user_id))
        self._conn.commit()
        return True
    
    def get_current_title(self, group_id: str, user_id: str) -> str:
        """获取当前佩戴头衔"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT current_title FROM user_data WHERE group_id = ? AND user_id = ?",
                       (group_id, user_id))
        row = cursor.fetchone()
        return row["current_title"] if row else ""
    
    # ========== 事件操作 ==========
    
    def add_global_event(self, group_id: str, event_type: str, duration_seconds: int, triggered_by: str = "") -> int:
        """添加全局事件，返回事件ID"""
        cursor = self._conn.cursor()
        expire_time = datetime.now().timestamp() + duration_seconds
        expire_str = datetime.fromtimestamp(expire_time).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO global_events (group_id, event_type, expire_time, triggered_by)
            VALUES (?, ?, ?, ?)
        """, (group_id, event_type, expire_str, triggered_by))
        self._conn.commit()
        return cursor.lastrowid
    
    def get_active_events(self, group_id: str) -> List[Dict]:
        """获取当前活跃事件"""
        cursor = self._conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            SELECT event_type, expire_time, triggered_by
            FROM global_events
            WHERE group_id = ? AND expire_time > ?
        """, (group_id, now))
        
        return [{"event_type": r["event_type"], "expire_time": r["expire_time"], 
                 "triggered_by": r["triggered_by"]} for r in cursor.fetchall()]
    
    def is_event_active(self, group_id: str, event_type: str) -> bool:
        """检查特定事件是否激活"""
        cursor = self._conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            SELECT 1 FROM global_events
            WHERE group_id = ? AND event_type = ? AND expire_time > ?
            LIMIT 1
        """, (group_id, event_type, now))
        
        return cursor.fetchone() is not None
    
    def cleanup_expired_events(self):
        """清理过期事件"""
        cursor = self._conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM global_events WHERE expire_time <= ?", (now,))
        self._conn.commit()
    
    # ========== 人设和对话操作 ==========
    
    def add_message(self, group_id: str, user_id: str, content: str) -> int:
        """添加消息到缓冲区，返回当前缓冲数量"""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO message_buffer (group_id, user_id, content)
            VALUES (?, ?, ?)
        """, (group_id, user_id, content))
        
        cursor.execute("""
            SELECT COUNT(*) FROM message_buffer WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        count = cursor.fetchone()[0]
        self._conn.commit()
        return count
    
    def get_buffer_messages(self, group_id: str, user_id: str) -> List[Dict]:
        """获取用户的缓冲消息"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT content, timestamp FROM message_buffer
            WHERE group_id = ? AND user_id = ?
            ORDER BY timestamp ASC
        """, (group_id, user_id))
        return [{"content": r["content"], "timestamp": r["timestamp"]} for r in cursor.fetchall()]
    
    def clear_buffer(self, group_id: str, user_id: str):
        """清空用户的缓冲消息"""
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM message_buffer WHERE group_id = ? AND user_id = ?", 
                       (group_id, user_id))
        self._conn.commit()
    
    def update_profile(self, group_id: str, user_id: str, profile: str, tags: List[str] = None):
        """更新用户人设"""
        cursor = self._conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        
        cursor.execute("""
            UPDATE user_data SET profile = ?, tags = ?, updated_at = ?
            WHERE group_id = ? AND user_id = ?
        """, (profile, tags_json, now, group_id, user_id))
        
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO user_data (group_id, user_id, profile, tags, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (group_id, user_id, profile, tags_json, now))
        
        self._conn.commit()
    
    def add_conversation(self, group_id: str, user_id: str, role: str, content: str):
        """添加对话记录"""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO conversation_history (group_id, user_id, role, content)
            VALUES (?, ?, ?, ?)
        """, (group_id, user_id, role, content))
        
        # 只保留最近20条
        cursor.execute("""
            DELETE FROM conversation_history 
            WHERE group_id = ? AND user_id = ? AND id NOT IN (
                SELECT id FROM conversation_history 
                WHERE group_id = ? AND user_id = ?
                ORDER BY timestamp DESC LIMIT 20
            )
        """, (group_id, user_id, group_id, user_id))
        self._conn.commit()
    
    def get_conversation(self, group_id: str, user_id: str, limit: int = 10) -> List[Dict]:
        """获取对话历史"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT role, content FROM conversation_history
            WHERE group_id = ? AND user_id = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (group_id, user_id, limit))
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    
    def add_memory(self, group_id: str, user_id: str, event: str):
        """添加重要事件记忆"""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO user_memories (group_id, user_id, event)
            VALUES (?, ?, ?)
        """, (group_id, user_id, event))
        
        # 只保留最近10条
        cursor.execute("""
            DELETE FROM user_memories 
            WHERE group_id = ? AND user_id = ? AND id NOT IN (
                SELECT id FROM user_memories 
                WHERE group_id = ? AND user_id = ?
                ORDER BY timestamp DESC LIMIT 10
            )
        """, (group_id, user_id, group_id, user_id))
        self._conn.commit()
    
    def get_memories(self, group_id: str, user_id: str) -> List[Dict]:
        """获取用户记忆"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT event, timestamp FROM user_memories
            WHERE group_id = ? AND user_id = ?
            ORDER BY timestamp DESC LIMIT 10
        """, (group_id, user_id))
        return [{"event": r["event"], "timestamp": r["timestamp"]} for r in cursor.fetchall()]
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# 全局实例
unified_db = UnifiedDatabase()
