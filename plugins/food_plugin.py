"""
吃什么 / 喝什么 插件
基于 HowToCook 程序员做饭指南
根据当前时间智能推荐菜品，返回图片、做法、卡路里
"""

import random
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.log import logger

from plugins.daily_utils import get_daily_seed

# HowToCook 菜谱目录
COOK_DIR = Path("/Users/znkj/PycharmProjects/HowToCook/dishes")

# 时间段 → 推荐分类映射
TIME_CATEGORY_MAP = {
    "breakfast":  (6, 10, ["breakfast"]),
    "morning_tea": (10, 11, ["drink", "dessert", "breakfast"]),
    "lunch":      (11, 14, ["meat_dish", "vegetable_dish", "aquatic", "staple", "soup"]),
    "afternoon_tea": (14, 17, ["drink", "dessert"]),
    "dinner":     (17, 21, ["meat_dish", "vegetable_dish", "aquatic", "staple", "soup"]),
    "midnight_snack": (21, 24, ["semi-finished", "staple", "breakfast"]),
    "late_night": (0, 6,   ["semi-finished", "staple", "breakfast"]),
}

# 分类中文名
CATEGORY_NAMES = {
    "breakfast": "早餐",
    "meat_dish": "荤菜",
    "vegetable_dish": "素菜",
    "aquatic": "水产",
    "staple": "主食",
    "soup": "汤品",
    "drink": "饮品",
    "dessert": "甜品",
    "semi-finished": "半成品",
    "condiment": "调料",
}


def get_time_period() -> Tuple[str, List[str]]:
    """根据当前时间段返回 (时段名, 推荐分类列表)"""
    hour = datetime.now().hour
    for period_name, (start, end, categories) in TIME_CATEGORY_MAP.items():
        if start <= hour < end:
            return period_name, categories
    # 默认
    return "lunch", ["meat_dish", "vegetable_dish", "aquatic", "staple", "soup"]


def get_time_period_label(period_name: str) -> str:
    """时段中文标签"""
    labels = {
        "breakfast": "🌅 早餐时间",
        "morning_tea": "☕ 上午茶时间",
        "lunch": "🌞 午餐时间",
        "afternoon_tea": "🍵 下午茶时间",
        "dinner": "🌆 晚餐时间",
        "midnight_snack": "🌙 夜宵时间",
        "late_night": "🌃 深夜食堂",
    }
    return labels.get(period_name, "🍽️ 吃饭时间")


def parse_dish_md(md_path: Path) -> Optional[Dict]:
    """
    解析菜谱 Markdown 文件
    返回: {name, category, calories, difficulty, ingredients, steps, image_path, description}
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"读取菜谱失败 {md_path}: {e}")
        return None

    name = md_path.stem  # 文件名去掉 .md

    # 分类 = 所在目录名
    category = md_path.parent.name
    # 如果在子目录里（带图片的菜），分类是上一级
    if category not in CATEGORY_NAMES:
        category = md_path.parent.parent.name if md_path.parent.parent.name in CATEGORY_NAMES else category

    # 提取卡路里
    calories = ""
    cal_match = re.search(r"预估卡路里[：:]\s*(.+)", text)
    if cal_match:
        calories = cal_match.group(1).strip()

    # 提取难度
    difficulty = ""
    diff_match = re.search(r"预估烹饪难度[：:]\s*(.+)", text)
    if diff_match:
        difficulty = diff_match.group(1).strip()

    # 提取描述（第一段正文，标题后的第一段非空文本）
    description = ""
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("![") and not line.startswith("预估"):
            description = line
            break

    # 提取必备原料
    ingredients = []
    in_ingredients = False
    for line in lines:
        stripped = line.strip()
        if "必备原料" in stripped or "原料和工具" in stripped:
            in_ingredients = True
            continue
        if in_ingredients:
            if stripped.startswith("- ") and stripped != "- ":
                ingredients.append(stripped[2:].strip())
            elif stripped.startswith("## "):  # 到下一个章节了
                break
            elif stripped == "":
                continue

    # 提取操作步骤
    steps = []
    in_steps = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## 操作") or stripped.startswith("## 步骤"):
            in_steps = True
            continue
        if in_steps:
            if re.match(r"^\d+\.\s", stripped):
                steps.append(stripped)
            elif stripped.startswith("## "):
                break
            elif stripped == "":
                continue

    # 查找图片
    image_path = find_dish_image(md_path, name)

    return {
        "name": name,
        "category": category,
        "calories": calories,
        "difficulty": difficulty,
        "description": description,
        "ingredients": ingredients,
        "steps": steps,
        "image_path": image_path,
        "file_path": md_path,
    }


def find_dish_image(md_path: Path, dish_name: str) -> Optional[Path]:
    """查找菜品图片：同目录下的 jpg/png，或同名目录下的图片"""
    parent = md_path.parent

    # 情况1: md 文件同目录下有同名图片
    for ext in ["jpg", "jpeg", "png", "webp"]:
        img = parent / f"{dish_name}.{ext}"
        if img.exists():
            return img

    # 情况2: md 在一个同名目录里，目录内有图片
    if parent.name == dish_name:
        for ext in ["jpg", "jpeg", "png", "webp"]:
            imgs = list(parent.glob(f"*.{ext}"))
            if imgs:
                return imgs[0]

    # 情况3: 随便找目录下的第一张图
    for ext in ["jpg", "jpeg", "png", "webp"]:
        imgs = list(parent.glob(f"*.{ext}"))
        if imgs:
            return imgs[0]

    return None


def scan_dishes(categories: List[str] = None) -> List[Dict]:
    """扫描所有菜谱，可按分类过滤"""
    dishes = []
    if not COOK_DIR.exists():
        logger.error(f"菜谱目录不存在: {COOK_DIR}")
        return dishes

    target_dirs = []
    if categories:
        for cat in categories:
            cat_dir = COOK_DIR / cat
            if cat_dir.exists():
                target_dirs.append(cat_dir)
    else:
        target_dirs = [d for d in COOK_DIR.iterdir() if d.is_dir() and d.name != "template"]

    for cat_dir in target_dirs:
        # 直接在分类目录下的 .md 文件
        for md_file in cat_dir.glob("*.md"):
            dish = parse_dish_md(md_file)
            if dish:
                dishes.append(dish)

        # 在子目录里的 .md 文件（带图片的菜）
        for sub_dir in cat_dir.iterdir():
            if sub_dir.is_dir():
                for md_file in sub_dir.glob("*.md"):
                    dish = parse_dish_md(md_file)
                    if dish:
                        dishes.append(dish)

    return dishes


def format_dish_message(dish: Dict, period_label: str) -> str:
    """格式化菜品消息"""
    lines = []
    lines.append(f"{period_label}")
    lines.append(f"━━━━━━━━━━━━━━━━")
    lines.append(f"🍽️ {dish['name']}")
    lines.append("")

    if dish["description"]:
        lines.append(f"📝 {dish['description']}")
        lines.append("")

    if dish["calories"]:
        lines.append(f"🔥 热量：{dish['calories']}")

    if dish["difficulty"]:
        lines.append(f"📊 难度：{dish['difficulty']}")

    if dish["ingredients"]:
        lines.append("")
        lines.append("🛒 【食材清单】")
        for ing in dish["ingredients"][:10]:  # 最多显示10样
            lines.append(f"  • {ing}")
        if len(dish["ingredients"]) > 10:
            lines.append(f"  ... 共 {len(dish['ingredients'])} 样")

    if dish["steps"]:
        lines.append("")
        lines.append("👨‍🍳 【做法步骤】")
        for step in dish["steps"][:8]:  # 最多显示8步
            lines.append(f"  {step}")
        if len(dish["steps"]) > 8:
            lines.append(f"  ... 共 {len(dish['steps'])} 步")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("💡 数据来源：程序员做饭指南")

    return "\n".join(lines)


# 缓存已扫描的菜品
_dish_cache: Dict[str, List[Dict]] = {}


def get_cached_dishes(categories: List[str] = None) -> List[Dict]:
    """带缓存的菜品扫描"""
    cache_key = ",".join(sorted(categories)) if categories else "all"
    if cache_key not in _dish_cache:
        _dish_cache[cache_key] = scan_dishes(categories)
        logger.info(f"扫描菜品 [{cache_key}]: {len(_dish_cache[cache_key])} 道")
    return _dish_cache[cache_key]


# ========== 注册命令 ==========

eat_cmd = on_command("吃什么", aliases={"今天吃什么", "吃啥", "饭点"}, priority=5, block=True)
drink_cmd = on_command("喝什么", aliases={"今天喝什么", "喝啥", "来一杯"}, priority=5, block=True)


@eat_cmd.handle()
async def handle_eat(bot: Bot, event: Event):
    """吃什么 - 根据时间智能推荐"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await eat_cmd.finish("请在群里问我吃什么喵~")
            return

        user_id = event.get_user_id()
        group_id = str(event.group_id)
        nickname = event.sender.card or event.sender.nickname or user_id

        # 根据时间段确定分类
        period_name, categories = get_time_period()
        period_label = get_time_period_label(period_name)

        # 获取菜品列表
        dishes = get_cached_dishes(categories)
        if not dishes:
            await eat_cmd.finish("没找到合适的菜谱，厨房可能还没准备好喵~")
            return

        # 用每日种子随机选一道（同一天同一用户同一道）
        seed_str = get_daily_seed(user_id, group_id) + "_eat"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        dish = rng.choice(dishes)

        # 构建消息
        msg = Message()

        # 先发图片
        if dish["image_path"] and dish["image_path"].exists():
            try:
                img_bytes = dish["image_path"].read_bytes()
                msg.append(MessageSegment.image(img_bytes))
            except Exception as e:
                logger.error(f"读取菜品图片失败: {e}")

        # 发文字
        text = format_dish_message(dish, period_label)
        msg.append(MessageSegment.at(user_id))
        msg.append(MessageSegment.text("\n" + text))

        await eat_cmd.finish(msg)

        logger.info(f"吃什么推荐: {nickname} → {dish['name']} ({period_name})")

    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"吃什么异常: {e}")


@drink_cmd.handle()
async def handle_drink(bot: Bot, event: Event):
    """喝什么 - 从饮品分类随机推荐"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await drink_cmd.finish("请在群里问我喝什么喵~")
            return

        user_id = event.get_user_id()
        group_id = str(event.group_id)
        nickname = event.sender.card or event.sender.nickname or user_id

        # 获取饮品列表
        dishes = get_cached_dishes(["drink"])
        if not dishes:
            await drink_cmd.finish("没找到饮品菜谱，厨房可能还没准备好喵~")
            return

        # 每日种子随机
        seed_str = get_daily_seed(user_id, group_id) + "_drink"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        dish = rng.choice(dishes)

        # 构建消息
        msg = Message()

        # 图片
        if dish["image_path"] and dish["image_path"].exists():
            try:
                img_bytes = dish["image_path"].read_bytes()
                msg.append(MessageSegment.image(img_bytes))
            except Exception as e:
                logger.error(f"读取饮品图片失败: {e}")

        # 文字
        text = format_dish_message(dish, "🥤 来一杯")
        msg.append(MessageSegment.at(user_id))
        msg.append(MessageSegment.text("\n" + text))

        await drink_cmd.finish(msg)

        logger.info(f"喝什么推荐: {nickname} → {dish['name']}")

    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"喝什么异常: {e}")
