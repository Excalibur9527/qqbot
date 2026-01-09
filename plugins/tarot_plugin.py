"""
今日塔罗牌插件
指令：今日塔罗、塔罗牌、占卜、抽塔罗
功能：每天给群友抽一张塔罗牌，同一天同一人结果固定
每天8点刷新，附带随机魔法猪图片
"""

import random
import hashlib
from pathlib import Path
from typing import Optional
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.log import logger

from plugins.daily_utils import get_daily_seed


# 图片目录
PLUGIN_DIR = Path(__file__).parent
MAGIC_PIG_DIR = PLUGIN_DIR / "magic_pig"

# 大阿尔卡纳 (Major Arcana) - 22张
MAJOR_ARCANA = [
    "愚者", "魔术师", "女教皇", "皇后", "皇帝", "教皇", "恋人", "战车",
    "力量", "隐士", "命运之轮", "正义", "倒吊人", "死神", "节制", "恶魔",
    "高塔", "星星", "月亮", "太阳", "审判", "世界"
]

# 小阿尔卡纳花色
SUITS = ["权杖", "圣杯", "宝剑", "星币"]
RANKS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "侍从", "骑士", "王后", "国王"]

# 牌意库
MEANINGS = {
    "愚者": "新的开始、冒险、纯真、自发性。代表着无限可能与勇敢踏出第一步。",
    "魔术师": "创造力、意志力、行动力、潜力。你拥有实现目标的一切资源。",
    "女教皇": "直觉、神秘、潜意识、冷静观察。相信你内心的声音。",
    "皇后": "丰饶、母性、创造、自然。享受生活的美好与富足。",
    "皇帝": "权威、结构、控制、父性。建立秩序，掌控局面。",
    "教皇": "传统、信仰、教导、精神指引。寻求智慧与指导。",
    "恋人": "爱情、和谐、选择、价值观的契合。面临重要的人生抉择。",
    "战车": "胜利、意志、决心、行动。勇往直前，克服障碍。",
    "力量": "勇气、耐心、内在力量、温柔。以柔克刚，内心强大。",
    "隐士": "内省、独处、寻求真理、智慧。向内探索，寻找答案。",
    "命运之轮": "命运、转折、机遇、循环。生命的起伏是自然规律。",
    "正义": "公正、真相、因果、平衡。诚实面对，承担责任。",
    "倒吊人": "牺牲、等待、新视角、放下。换个角度看问题。",
    "死神": "结束、转变、重生、告别过去。旧的结束是新的开始。",
    "节制": "平衡、耐心、调和、中庸。保持适度，和谐共处。",
    "恶魔": "束缚、诱惑、物质、阴暗面。警惕内心的欲望与执念。",
    "高塔": "剧变、灾难、真相大白、打破旧习。突如其来的改变带来觉醒。",
    "星星": "希望、灵感、宁静、信心。黑暗过后必有光明。",
    "月亮": "幻觉、恐惧、潜意识、不确定。面对内心的迷茫与不安。",
    "太阳": "成功、快乐、活力、自信。光明正大，充满能量。",
    "审判": "觉醒、重生、反思、召唤。倾听内心的呼唤，做出改变。",
    "世界": "达成、圆满、旅行、一个阶段的终结。完成使命，迎接新篇章。",
}

# 逆位解读前缀
REVERSED_PREFIX = [
    "（逆位）需要反向思考：",
    "（逆位）警示你注意：",
    "（逆位）提醒你反思：",
]


def find_magic_pig_images() -> list:
    """查找所有魔法猪图片"""
    if not MAGIC_PIG_DIR.exists():
        return []
    exts = ["png", "jpg", "jpeg", "webp", "gif"]
    images = []
    for ext in exts:
        images.extend(MAGIC_PIG_DIR.glob(f"*.{ext}"))
    return images


def get_daily_tarot(user_id: str, group_id: str) -> dict:
    """
    根据用户ID和群ID生成固定的今日塔罗牌
    每天8点刷新
    返回: {card_name, orientation, meaning, is_major, image_path}
    """
    seed_str = get_daily_seed(user_id, group_id)
    seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    rng = random.Random(seed)
    
    # 40% 概率抽到大阿尔卡纳（增加珍稀感）
    if rng.random() < 0.4:
        card_name = rng.choice(MAJOR_ARCANA)
        is_major = True
    else:
        suit = rng.choice(SUITS)
        rank = rng.choice(RANKS)
        card_name = f"{suit}{rank}"
        is_major = False
    
    # 50% 概率正位/逆位
    is_upright = rng.random() > 0.5
    orientation = "正位" if is_upright else "逆位"
    
    # 获取牌意
    base_meaning = MEANINGS.get(card_name, "命运的指引正处于迷雾中，请用心感悟。")
    if is_upright:
        meaning = base_meaning
    else:
        prefix = rng.choice(REVERSED_PREFIX)
        meaning = prefix + base_meaning
    
    # 随机选择一张魔法猪图片
    images = find_magic_pig_images()
    image_path = rng.choice(images) if images else None
    
    return {
        "card_name": card_name,
        "orientation": orientation,
        "meaning": meaning,
        "is_major": is_major,
        "image_path": image_path
    }


# 注册命令
tarot_cmd = on_command("今日塔罗", aliases={"塔罗牌", "占卜", "抽塔罗", "塔罗"}, priority=5, block=True)


@tarot_cmd.handle()
async def handle_tarot(bot: Bot, event: Event):
    """抽今日塔罗牌"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await tarot_cmd.finish("请在群里占卜喵~")
            return
        
        user_id = event.get_user_id()
        group_id = str(event.group_id)
        
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        # 获取今日塔罗
        result = get_daily_tarot(user_id, group_id)
        
        card_name = result["card_name"]
        orientation = result["orientation"]
        meaning = result["meaning"]
        is_major = result["is_major"]
        image_path = result["image_path"]
        
        # 大阿尔卡纳标记
        arcana_mark = "【大阿尔卡纳】" if is_major else ""
        
        # 构建消息
        msg = Message()
        
        # 添加图片
        if image_path and image_path.exists():
            try:
                img_bytes = image_path.read_bytes()
                msg.append(MessageSegment.image(img_bytes))
            except Exception as e:
                logger.error(f"读取塔罗图片失败: {e}")
        
        # 构建文案
        text_lines = [
            f"\n✨ --- 占卜之镜 --- ✨",
            f"👤 占卜者：{nickname}",
            f"--------------------",
            f"🔮 抽取牌面：【{card_name}】{arcana_mark}",
            f"💡 当前状态：{orientation}",
            f"📝 牌意解析：{meaning}",
            f"--------------------",
            f"🌟 塔罗仅供参考，命运掌握在自己手中喵~"
        ]
        
        msg.append(MessageSegment.at(user_id))
        msg.append(MessageSegment.text("\n".join(text_lines)))
        
        await tarot_cmd.finish(msg)
        
        logger.info(f"塔罗占卜: {nickname} 抽到 {card_name} {orientation}")
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"塔罗占卜异常: {e}")
