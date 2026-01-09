"""
群友人设数据库模块
使用 SQLite 存储消息缓冲、用户人设、对话历史、重要事件
"""

import sqlite3
import threading
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from nonebot.log import logger


class ProfileDatabase:
    """群友人设数据库管理器"""
    
    def __init__(self, db_path: str = "data/profiles.db"):
        """初始化数据库连接，自动创建表结构"""
        self.db_path = db_path
        self._local = threading.local()
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
        logger.info(f"ProfileDatabase 初始化完成: {db_path}")
    
    @property
    def _conn(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_tables(self) -> None:
        """创建数据库表结构"""
        conn = self._conn
        cursor = conn.cursor()
        
        # 消息缓冲表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_buffer_group_user 
            ON message_buffer(group_id, user_id)
        """)
        
        # 用户人设表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                nickname TEXT,
                profile TEXT,
                tags TEXT,
                message_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id)
            )
        """)
        
        # 检查并添加缺失的列（兼容旧数据库）
        try:
            cursor.execute("SELECT tags FROM user_profile LIMIT 1")
        except sqlite3.OperationalError:
            logger.info("迁移数据库：添加 tags 列")
            cursor.execute("ALTER TABLE user_profile ADD COLUMN tags TEXT DEFAULT '[]'")
        
        # 对话历史表
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
            CREATE INDEX IF NOT EXISTS idx_conv_group_user 
            ON conversation_history(group_id, user_id)
        """)
        
        # 重要事件记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                event TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_group_user 
            ON user_memories(group_id, user_id)
        """)
        
        conn.commit()
    
    # ========== 消息缓冲相关 ==========
    
    def add_message(self, group_id: str, user_id: str, content: str) -> int:
        """添加消息到缓冲区，返回当前缓冲数量"""
        conn = self._conn
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO message_buffer (group_id, user_id, content)
            VALUES (?, ?, ?)
        """, (group_id, user_id, content))
        
        cursor.execute("""
            SELECT COUNT(*) FROM message_buffer
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        
        count = cursor.fetchone()[0]
        conn.commit()
        return count
    
    def get_buffer_messages(self, group_id: str, user_id: str) -> List[Dict]:
        """获取用户的缓冲消息列表"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT content, timestamp FROM message_buffer
            WHERE group_id = ? AND user_id = ?
            ORDER BY timestamp ASC
        """, (group_id, user_id))
        
        return [{"content": row["content"], "timestamp": row["timestamp"]} for row in cursor.fetchall()]
    
    def clear_buffer(self, group_id: str, user_id: str) -> None:
        """清空用户的缓冲消息"""
        conn = self._conn
        cursor = conn.cursor()
        cursor.execute("DELETE FROM message_buffer WHERE group_id = ? AND user_id = ?", (group_id, user_id))
        conn.commit()
    
    # ========== 用户人设相关 ==========
    
    def get_profile(self, group_id: str, user_id: str) -> Optional[Dict]:
        """获取用户人设"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT group_id, user_id, nickname, profile, tags, message_count, created_at, updated_at
            FROM user_profile WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        tags = []
        if row["tags"]:
            try:
                tags = json.loads(row["tags"])
            except:
                tags = []
        
        return {
            "group_id": row["group_id"],
            "user_id": row["user_id"],
            "nickname": row["nickname"],
            "profile": row["profile"],
            "tags": tags,
            "message_count": row["message_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    
    def update_profile(self, group_id: str, user_id: str, nickname: str, profile: str, 
                       message_count_delta: int, tags: List[str] = None) -> None:
        """更新或插入用户人设"""
        conn = self._conn
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO user_profile (group_id, user_id, nickname, profile, tags, message_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(group_id, user_id) DO UPDATE SET
                nickname = COALESCE(excluded.nickname, user_profile.nickname),
                profile = excluded.profile,
                tags = excluded.tags,
                message_count = user_profile.message_count + excluded.message_count,
                updated_at = excluded.updated_at
        """, (group_id, user_id, nickname, profile, tags_json, message_count_delta, now))
        conn.commit()
    
    def update_nickname(self, group_id: str, user_id: str, nickname: str) -> None:
        """只更新用户昵称"""
        conn = self._conn
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO user_profile (group_id, user_id, nickname, profile, tags, message_count, updated_at)
            VALUES (?, ?, ?, '', '[]', 0, ?)
            ON CONFLICT(group_id, user_id) DO UPDATE SET
                nickname = excluded.nickname,
                updated_at = excluded.updated_at
        """, (group_id, user_id, nickname, now))
        conn.commit()
    
    # ========== 对话历史相关（持久化连续对话） ==========
    
    def add_conversation(self, group_id: str, user_id: str, role: str, content: str) -> None:
        """添加对话记录"""
        conn = self._conn
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversation_history (group_id, user_id, role, content)
            VALUES (?, ?, ?, ?)
        """, (group_id, user_id, role, content))
        conn.commit()
        
        # 只保留最近 20 条
        cursor.execute("""
            DELETE FROM conversation_history 
            WHERE group_id = ? AND user_id = ? AND id NOT IN (
                SELECT id FROM conversation_history 
                WHERE group_id = ? AND user_id = ?
                ORDER BY timestamp DESC LIMIT 20
            )
        """, (group_id, user_id, group_id, user_id))
        conn.commit()
    
    def get_conversation(self, group_id: str, user_id: str, limit: int = 10) -> List[Dict]:
        """获取对话历史"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT role, content FROM conversation_history
            WHERE group_id = ? AND user_id = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (group_id, user_id, limit))
        
        rows = cursor.fetchall()
        # 反转顺序，让最早的在前面
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
    
    # ========== 重要事件记忆相关 ==========
    
    def add_memory(self, group_id: str, user_id: str, event: str) -> None:
        """添加重要事件记忆"""
        conn = self._conn
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_memories (group_id, user_id, event)
            VALUES (?, ?, ?)
        """, (group_id, user_id, event))
        conn.commit()
        
        # 只保留最近 10 条记忆
        cursor.execute("""
            DELETE FROM user_memories 
            WHERE group_id = ? AND user_id = ? AND id NOT IN (
                SELECT id FROM user_memories 
                WHERE group_id = ? AND user_id = ?
                ORDER BY timestamp DESC LIMIT 10
            )
        """, (group_id, user_id, group_id, user_id))
        conn.commit()
    
    def get_memories(self, group_id: str, user_id: str) -> List[Dict]:
        """获取用户的重要事件记忆"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT event, timestamp FROM user_memories
            WHERE group_id = ? AND user_id = ?
            ORDER BY timestamp DESC LIMIT 10
        """, (group_id, user_id))
        
        return [{"event": row["event"], "timestamp": row["timestamp"]} for row in cursor.fetchall()]
    
    def get_all_profiles(self, group_id: str) -> List[Dict]:
        """获取某个群的所有用户人设"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT group_id, user_id, nickname, profile, tags, message_count, created_at, updated_at
            FROM user_profile WHERE group_id = ? ORDER BY message_count DESC
        """, (group_id,))
        
        result = []
        for row in cursor.fetchall():
            tags = []
            if row["tags"]:
                try:
                    tags = json.loads(row["tags"])
                except:
                    tags = []
            result.append({
                "group_id": row["group_id"],
                "user_id": row["user_id"],
                "nickname": row["nickname"],
                "profile": row["profile"],
                "tags": tags,
                "message_count": row["message_count"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })
        return result
    
    def close(self) -> None:
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
