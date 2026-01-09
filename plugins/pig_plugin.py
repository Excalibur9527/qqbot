"""
Roll Pig Plugin - Local Implementation
Migrated from nonebot-plugin-rollpig, sending images directly.
每天8点刷新
"""

import json
import random
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.log import logger

from plugins.daily_utils import get_daily_seed

# Paths
PLUGIN_DIR = Path(__file__).parent
PROJECT_ROOT = PLUGIN_DIR.parent
RESOURCE_DIR = PROJECT_ROOT / "resources" / "pig"
PIG_INFO_PATH = RESOURCE_DIR / "pig.json"
IMAGE_DIR = RESOURCE_DIR / "image"
DATA_DIR = PROJECT_ROOT / "data"
TODAY_RECORD_PATH = DATA_DIR / "pig_records.json"

# Create data dir if not exists
if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load pig data
def load_pig_data() -> List[Dict]:
    if not PIG_INFO_PATH.exists():
        logger.error(f"Pig info file not found at {PIG_INFO_PATH}")
        return []
    try:
        return json.loads(PIG_INFO_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to load pig info: {e}")
        return []

PIG_LIST = load_pig_data()
if not PIG_LIST:
    logger.warning("Pig list is empty! Plugin will not work correctly.")

# Find image file
def find_image_file(pig_id: str) -> Optional[Path]:
    exts = ["png", "jpg", "jpeg", "webp", "gif"]
    for ext in exts:
        file = IMAGE_DIR / f"{pig_id}.{ext}"
        if file.exists():
            return file
    return None

# Persistence helpers
def load_records() -> Dict:
    if not TODAY_RECORD_PATH.exists():
        return {"date": "", "records": {}}
    try:
        return json.loads(TODAY_RECORD_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"date": "", "records": {}}

def save_records(data: Dict):
    TODAY_RECORD_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# Logic to pick a pig
def pick_random_pig() -> Dict:
    if not PIG_LIST:
        return {}
    return random.choice(PIG_LIST)

def pick_daily_pig(user_id: str, group_id: str = "") -> Dict:
    """根据用户ID和日期选择固定的今日小猪（8点刷新）"""
    if not PIG_LIST:
        return {}
    seed_str = get_daily_seed(user_id, group_id)
    seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    rng = random.Random(seed)
    return rng.choice(PIG_LIST)

# Commands
today_pig_cmd = on_command("今天是什么小猪", aliases={"今日小猪", "抽小猪"}, block=True)
random_pig_cmd = on_command("随机小猪", block=True)

@today_pig_cmd.handle()
async def handle_today_pig(bot: Bot, event: Event):
    user_id = str(event.get_user_id())
    group_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else ""
    
    if not PIG_LIST:
        await today_pig_cmd.finish("猪圈现在是空的，稍后再来吧！")
        return
    
    # 使用8点刷新的每日固定小猪
    pig = pick_daily_pig(user_id, group_id)
    logger.info(f"User {user_id} got daily pig: {pig.get('name')}")
    
    await send_pig_result(today_pig_cmd, pig, prefix="今天你是：")

@random_pig_cmd.handle()
async def handle_random_pig(bot: Bot, event: Event):
    if not PIG_LIST:
        await random_pig_cmd.finish("猪圈现在是空的，稍后再来吧！")
        return
    
    pig = pick_random_pig()
    await send_pig_result(random_pig_cmd, pig, prefix="随机捕捉到一只：")

async def send_pig_result(matcher, pig: Dict, prefix: str = ""):
    pig_id = pig.get("id", "")
    name = pig.get("name", "未知猪")
    desc = pig.get("description", "")
    analysis = pig.get("analysis", "")
    
    img_path = find_image_file(pig_id)
    
    msg = Message()
    if img_path:
        # Read file as bytes to avoid path issues between containers
        try:
            img_bytes = img_path.read_bytes()
            msg.append(MessageSegment.image(img_bytes))
        except Exception as e:
            logger.error(f"Failed to read image {img_path}: {e}")
            msg.append(MessageSegment.text("[图片读取失败] "))
    else:
        msg.append(MessageSegment.text("[图片走丢了] "))
        
    text_content = f"\n{prefix}{name}\n\n{desc}\n\n{analysis}"
    msg.append(MessageSegment.text(text_content))
    
    await matcher.finish(msg)
