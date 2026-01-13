"""
数据迁移脚本
从 woodfish.db 和 profiles.db 迁移数据到 unified_data.db
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from nonebot.log import logger


def migrate_data():
    """执行数据迁移"""
    unified_path = "data/unified_data.db"
    woodfish_path = "data/woodfish.db"
    profiles_path = "data/profiles.db"
    
    # 检查是否已迁移
    marker_path = Path("data/.migrated")
    if marker_path.exists():
        logger.info("数据已迁移，跳过")
        return
    
    logger.info("开始数据迁移...")
    
    # 确保 data 目录存在
    Path("data").mkdir(parents=True, exist_ok=True)
    
    # 先初始化统一数据库（创建表）
    from plugins.unified_db import unified_db
    
    # 连接统一数据库
    unified_conn = sqlite3.connect(unified_path)
    unified_conn.row_factory = sqlite3.Row
    unified_cursor = unified_conn.cursor()
    
    migrated_count = 0
    
    # 迁移功德数据
    if Path(woodfish_path).exists():
        logger.info(f"迁移功德数据: {woodfish_path}")
        woodfish_conn = sqlite3.connect(woodfish_path)
        woodfish_conn.row_factory = sqlite3.Row
        woodfish_cursor = woodfish_conn.cursor()
        
        try:
            woodfish_cursor.execute("SELECT * FROM merit")
            for row in woodfish_cursor.fetchall():
                unified_cursor.execute("""
                    INSERT INTO user_data (
                        group_id, user_id, nickname, 
                        total_merit, today_merit, today_date, knock_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(group_id, user_id) DO UPDATE SET
                        total_merit = excluded.total_merit,
                        today_merit = excluded.today_merit,
                        today_date = excluded.today_date,
                        knock_count = excluded.knock_count,
                        nickname = COALESCE(excluded.nickname, user_data.nickname)
                """, (
                    row["group_id"], row["user_id"], row["nickname"],
                    row["total_merit"], row["today_merit"], 
                    row["today_date"], row["knock_count"]
                ))
                migrated_count += 1
            logger.info(f"功德数据迁移完成: {migrated_count} 条")
        except Exception as e:
            logger.error(f"功德数据迁移失败: {e}")
        finally:
            woodfish_conn.close()
    
    # 迁移人设数据
    if Path(profiles_path).exists():
        logger.info(f"迁移人设数据: {profiles_path}")
        profiles_conn = sqlite3.connect(profiles_path)
        profiles_conn.row_factory = sqlite3.Row
        profiles_cursor = profiles_conn.cursor()
        
        profile_count = 0
        try:
            profiles_cursor.execute("SELECT * FROM user_profile")
            for row in profiles_cursor.fetchall():
                unified_cursor.execute("""
                    INSERT INTO user_data (
                        group_id, user_id, nickname, profile, tags, message_count
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(group_id, user_id) DO UPDATE SET
                        profile = excluded.profile,
                        tags = excluded.tags,
                        message_count = excluded.message_count,
                        nickname = COALESCE(excluded.nickname, user_data.nickname)
                """, (
                    row["group_id"], row["user_id"], row["nickname"],
                    row["profile"], row["tags"], row["message_count"]
                ))
                profile_count += 1
            logger.info(f"人设数据迁移完成: {profile_count} 条")
        except Exception as e:
            logger.error(f"人设数据迁移失败: {e}")
        
        # 迁移对话历史
        conv_count = 0
        try:
            profiles_cursor.execute("SELECT * FROM conversation_history")
            for row in profiles_cursor.fetchall():
                unified_cursor.execute("""
                    INSERT INTO conversation_history (group_id, user_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (row["group_id"], row["user_id"], row["role"], row["content"], row["timestamp"]))
                conv_count += 1
            logger.info(f"对话历史迁移完成: {conv_count} 条")
        except Exception as e:
            logger.error(f"对话历史迁移失败: {e}")
        
        # 迁移消息缓冲
        buffer_count = 0
        try:
            profiles_cursor.execute("SELECT * FROM message_buffer")
            for row in profiles_cursor.fetchall():
                unified_cursor.execute("""
                    INSERT INTO message_buffer (group_id, user_id, content, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (row["group_id"], row["user_id"], row["content"], row["timestamp"]))
                buffer_count += 1
            logger.info(f"消息缓冲迁移完成: {buffer_count} 条")
        except Exception as e:
            logger.error(f"消息缓冲迁移失败: {e}")
        
        # 迁移用户记忆
        memory_count = 0
        try:
            profiles_cursor.execute("SELECT * FROM user_memories")
            for row in profiles_cursor.fetchall():
                unified_cursor.execute("""
                    INSERT INTO user_memories (group_id, user_id, event, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (row["group_id"], row["user_id"], row["event"], row["timestamp"]))
                memory_count += 1
            logger.info(f"用户记忆迁移完成: {memory_count} 条")
        except Exception as e:
            logger.error(f"用户记忆迁移失败: {e}")
        
        profiles_conn.close()
    
    unified_conn.commit()
    unified_conn.close()
    
    # 标记迁移完成
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(datetime.now().isoformat())
    
    logger.info(f"数据迁移全部完成！共迁移 {migrated_count} 条功德记录")


if __name__ == "__main__":
    migrate_data()
