"""
Random Pig Plugin V2 - PigHub API Implementation
从 PigHub API 获取随机小猪图片
"""

import random
from typing import Optional, Dict, List

import httpx
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.log import logger

# PigHub API
PIGHUB_API = "https://pighub.top/api/all-images"
PIGHUB_BASE = "https://pighub.top"

# Cache for images list
_images_cache: Optional[List[Dict]] = None

async def fetch_pighub_images() -> List[Dict]:
    """从 PigHub API 获取所有图片列表"""
    global _images_cache
    
    # 如果有缓存，直接返回
    if _images_cache is not None:
        return _images_cache
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(PIGHUB_API)
            response.raise_for_status()
            data = response.json()
            
            images = data.get("images", [])
            if images:
                _images_cache = images
                logger.info(f"Fetched {len(images)} images from PigHub")
                return images
            else:
                logger.warning("No images found in PigHub response")
                return []
                
    except Exception as e:
        logger.error(f"Failed to fetch PigHub images: {e}")
        return []

def get_random_pig(images: List[Dict]) -> Optional[Dict]:
    """从图片列表中随机选择一张"""
    if not images:
        return None
    return random.choice(images)

async def download_pig_image(thumbnail_url: str) -> Optional[bytes]:
    """下载小猪图片"""
    try:
        full_url = f"{PIGHUB_BASE}{thumbnail_url}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(full_url)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"Failed to download pig image from {thumbnail_url}: {e}")
        return None

# Command
random_pighub_cmd = on_command("随机小猪", block=True, priority=5)

@random_pighub_cmd.handle()
async def handle_random_pighub(bot: Bot, event: Event):
    """处理随机小猪命令"""
    
    # 获取图片列表
    images = await fetch_pighub_images()
    
    if not images:
        await random_pighub_cmd.finish("小猪跑丢了，稍后再试试吧！")
        return
    
    # 随机选择一张
    pig = get_random_pig(images)
    
    if not pig:
        await random_pighub_cmd.finish("没有找到小猪，稍后再试试吧！")
        return
    
    # 获取图片信息
    title = pig.get("title", "神秘小猪")
    thumbnail = pig.get("thumbnail", "")
    
    # 下载图片
    img_bytes = await download_pig_image(thumbnail)
    
    # 构建消息
    msg = Message()
    
    if img_bytes:
        msg.append(MessageSegment.image(img_bytes))
    else:
        msg.append(MessageSegment.text("[图片加载失败] "))
    
    msg.append(MessageSegment.text(f"\n随机捕捉到一只：{title}"))
    
    await random_pighub_cmd.finish(msg)
