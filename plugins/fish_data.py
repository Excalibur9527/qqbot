"""
鱼类数据定义
包含200种水生物：100普通 + 30稀有 + 20史诗 + 50暗黑(与其他重叠) + 50闪光(与其他重叠)
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class Rarity(Enum):
    COMMON = "common"      # 普通 70%
    RARE = "rare"          # 稀有 20%
    EPIC = "epic"          # 史诗 8%
    LEGENDARY = "legendary" # 传说 2%


@dataclass
class Fish:
    """鱼类数据"""
    id: str              # 唯一标识
    name: str            # 显示名称
    rarity: Rarity       # 稀有度
    is_dark: bool        # 是否暗黑
    is_shiny: bool       # 是否闪光
    min_length: float    # 最小长度(cm)
    max_length: float    # 最大长度(cm)
    active_start: int    # 活动开始时间(0-23)
    active_end: int      # 活动结束时间(0-23)
    emoji: str           # 显示emoji
    description: str = "" # 描述
    image_id: str = ""   # 图片文件名(不含扩展名)，为空表示无图片
    
    def is_active(self, hour: int) -> bool:
        """检查当前时间是否在活动时间内"""
        if self.active_start <= self.active_end:
            return self.active_start <= hour < self.active_end
        else:  # 跨夜，如 22-6
            return hour >= self.active_start or hour < self.active_end


# ========== 普通鱼类 (100种) ==========
COMMON_FISH = [
    # 白天常见鱼 (60种) 6:00-22:00
    Fish("goldfish", "小金鱼", Rarity.COMMON, False, False, 3, 8, 6, 22, "🐠", "最常见的观赏鱼", "金鱼"),
    Fish("carp", "鲤鱼", Rarity.COMMON, False, False, 15, 45, 6, 20, "🐟", "年年有余", "鲤鱼"),
    Fish("crucian", "鲫鱼", Rarity.COMMON, False, False, 10, 25, 6, 20, "🐟", "煲汤首选", "鲫鱼"),
    Fish("grass_carp", "草鱼", Rarity.COMMON, False, False, 30, 80, 8, 18, "🐟", "四大家鱼之一", "草鱼"),
    Fish("silver_carp", "鲢鱼", Rarity.COMMON, False, False, 25, 60, 8, 18, "🐟", "喜欢跳跃", "鲢鱼"),
    Fish("bighead_carp", "鳙鱼", Rarity.COMMON, False, False, 30, 70, 8, 18, "🐟", "大头鱼", "鳙鱼"),
    Fish("catfish", "鲶鱼", Rarity.COMMON, False, False, 20, 60, 6, 22, "🐡", "胡子很长", "鲶鱼"),
    Fish("tilapia", "罗非鱼", Rarity.COMMON, False, False, 15, 35, 8, 18, "🐟", "非洲鲫鱼", "罗非鱼"),
    Fish("perch", "鲈鱼", Rarity.COMMON, False, False, 20, 50, 8, 18, "🐟", "清蒸最佳", "鲈鱼"),
    Fish("bream", "鳊鱼", Rarity.COMMON, False, False, 15, 35, 8, 18, "🐟", "武昌鱼", "鳊鱼"),
    Fish("mandarin_fish", "鳜鱼", Rarity.COMMON, False, False, 20, 45, 10, 18, "🐟", "桃花流水鳜鱼肥", "鳜鱼"),
    Fish("yellow_catfish", "黄颡鱼", Rarity.COMMON, False, False, 10, 25, 8, 20, "🐡", "黄辣丁", "黄颡鱼"),
    Fish("snakehead", "黑鱼", Rarity.COMMON, False, False, 25, 60, 8, 20, "🐟", "生鱼片", "黑鱼"),
    Fish("mud_carp", "鲮鱼", Rarity.COMMON, False, False, 15, 35, 8, 18, "🐟", "做鱼丸", "鲮鱼"),
    Fish("white_amur", "青鱼", Rarity.COMMON, False, False, 40, 100, 8, 18, "🐟", "四大家鱼之首", "青鱼"),
    
    Fish("shrimp", "小河虾", Rarity.COMMON, False, False, 2, 6, 6, 20, "🦐", "透明的小家伙", "小河虾"),
    Fish("crayfish", "小龙虾", Rarity.COMMON, False, False, 8, 15, 10, 22, "🦞", "麻辣小龙虾", "小龙虾"),
    Fish("snail", "田螺", Rarity.COMMON, False, False, 2, 5, 6, 22, "🐚", "嗦螺", "田螺"),
    Fish("clam", "河蚌", Rarity.COMMON, False, False, 5, 15, 6, 20, "🐚", "可能有珍珠", "河蚌"),
    Fish("frog", "青蛙", Rarity.COMMON, False, False, 5, 12, 6, 22, "🐸", "呱呱叫", "青蛙"),
    Fish("tadpole", "蝌蚪", Rarity.COMMON, False, False, 1, 3, 8, 18, "🔘", "小蝌蚪找妈妈", "蝌蚪"),
    Fish("pond_loach", "泥鳅", Rarity.COMMON, False, False, 8, 18, 6, 20, "🐛", "滑溜溜", "泥鳅"),
    Fish("weatherfish", "气象鱼", Rarity.COMMON, False, False, 10, 20, 8, 18, "🐟", "能预测天气", "气象鱼"),
    Fish("minnow", "鲦鱼", Rarity.COMMON, False, False, 3, 8, 8, 18, "🐟", "小杂鱼", "鲦鱼"),
    Fish("gudgeon", "麦穗鱼", Rarity.COMMON, False, False, 3, 8, 8, 18, "🐟", "钓鱼人的噩梦", "麦穗鱼"),
    
    Fish("topmouth", "餐条", Rarity.COMMON, False, False, 5, 12, 8, 18, "🐟", "白条鱼", "餐条"),
    Fish("roach", "拟鲤", Rarity.COMMON, False, False, 10, 25, 8, 18, "🐟", "欧洲常见", "拟鲤"),
    Fish("rudd", "红鳍鲌", Rarity.COMMON, False, False, 15, 30, 8, 18, "🐟", "红色鱼鳍", "红鳍鲌"),
    Fish("tench", "丁鱥", Rarity.COMMON, False, False, 20, 45, 8, 18, "🐟", "医生鱼", "丁鱥"),
    Fish("ide", "雅罗鱼", Rarity.COMMON, False, False, 25, 50, 8, 18, "🐟", "北方鱼类", "雅罗鱼"),
    Fish("chub", "鲢", Rarity.COMMON, False, False, 20, 45, 8, 18, "🐟", "圆滚滚", "鲢"),
    Fish("dace", "雅罗", Rarity.COMMON, False, False, 15, 30, 8, 18, "🐟", "溪流鱼", "雅罗"),
    Fish("bleak", "欧鳊", Rarity.COMMON, False, False, 10, 20, 8, 18, "🐟", "银色闪闪", "欧鳊"),
    Fish("barbel", "鲃鱼", Rarity.COMMON, False, False, 30, 70, 8, 18, "🐟", "有胡须", "鲃鱼"),
    Fish("nase", "鲴鱼", Rarity.COMMON, False, False, 20, 40, 8, 18, "🐟", "吃藻类", "鲴鱼"),
    
    Fish("guppy", "孔雀鱼", Rarity.COMMON, False, False, 2, 5, 8, 18, "🐠", "五彩斑斓", "孔雀鱼"),
    Fish("molly", "茉莉鱼", Rarity.COMMON, False, False, 3, 8, 8, 18, "🐠", "黑色小鱼", "茉莉鱼"),
    Fish("platy", "月光鱼", Rarity.COMMON, False, False, 3, 6, 8, 18, "🐠", "橙红色", "月光鱼"),
    Fish("swordtail", "剑尾鱼", Rarity.COMMON, False, False, 5, 12, 8, 18, "🐠", "尾巴像剑", "剑尾鱼"),
    Fish("tetra", "灯鱼", Rarity.COMMON, False, False, 2, 5, 8, 18, "🐠", "霓虹灯", "灯鱼"),
    Fish("danio", "斑马鱼", Rarity.COMMON, False, False, 3, 6, 8, 18, "🐠", "条纹明显", "斑马鱼"),
    Fish("rasbora", "波鱼", Rarity.COMMON, False, False, 2, 5, 8, 18, "🐠", "群游", "波鱼"),
    Fish("barb", "虎皮鱼", Rarity.COMMON, False, False, 3, 7, 8, 18, "🐠", "虎纹", "虎皮鱼"),
    Fish("corydoras", "鼠鱼", Rarity.COMMON, False, False, 3, 7, 8, 18, "🐠", "清道夫", "鼠鱼"),
    Fish("pleco", "异型鱼", Rarity.COMMON, False, False, 5, 15, 8, 20, "🐠", "吸盘嘴", "异型鱼"),
    
    Fish("bitterling", "鳑鲏", Rarity.COMMON, False, False, 3, 8, 8, 18, "🐟", "彩虹色", "鳑鲏"),
    Fish("stone_loach", "花鳅", Rarity.COMMON, False, False, 5, 12, 8, 18, "🐛", "躲石头下", "花鳅"),
    Fish("spined_loach", "刺鳅", Rarity.COMMON, False, False, 8, 15, 8, 18, "🐛", "有小刺", "刺鳅"),
    Fish("bullhead", "塘鳢", Rarity.COMMON, False, False, 8, 18, 8, 20, "🐡", "大头", "塘鳢"),
    Fish("goby", "虾虎鱼", Rarity.COMMON, False, False, 3, 10, 8, 20, "🐟", "趴在石头上", "虾虎鱼"),
    Fish("sculpin", "杜父鱼", Rarity.COMMON, False, False, 8, 20, 8, 18, "🐡", "丑萌", "杜父鱼"),
    Fish("stickleback", "刺鱼", Rarity.COMMON, False, False, 3, 8, 8, 18, "🐟", "背上有刺", "刺鱼"),
    Fish("killifish", "鳉鱼", Rarity.COMMON, False, False, 3, 8, 8, 18, "🐠", "年鱼", "鳉鱼"),
    Fish("ricefish", "青鳉", Rarity.COMMON, False, False, 2, 4, 8, 18, "🐠", "稻田鱼", "青鳉"),
    Fish("mosquitofish", "食蚊鱼", Rarity.COMMON, False, False, 2, 5, 8, 20, "🐠", "灭蚊小能手", "食蚊鱼"),
    
    # 夜间常见鱼 (20种) 20:00-8:00
    Fish("eel", "鳗鱼", Rarity.COMMON, False, False, 30, 80, 20, 8, "🐍", "滑不溜秋", "鳗鱼"),
    Fish("loach", "夜鳅", Rarity.COMMON, False, False, 10, 20, 20, 8, "🐛", "夜行性", "夜鳅"),
    Fish("night_catfish", "夜鲶", Rarity.COMMON, False, False, 25, 55, 22, 6, "🐡", "夜间活动", "夜鲶"),
    Fish("night_carp", "夜鲤", Rarity.COMMON, False, False, 20, 50, 22, 6, "🐟", "月下游泳", "夜鲤"),
    Fish("night_shrimp", "夜虾", Rarity.COMMON, False, False, 3, 8, 22, 6, "🦐", "透明发光", "夜虾"),
    Fish("firefly_squid", "萤火虫鱿", Rarity.COMMON, False, False, 5, 10, 22, 4, "🦑", "会发光", "萤火虫鱿"),
    Fish("lanternfish", "灯笼鱼", Rarity.COMMON, False, False, 3, 8, 22, 6, "🐟", "自带照明", "灯笼鱼"),
    Fish("moonfish", "月亮鱼", Rarity.COMMON, False, False, 10, 25, 22, 6, "🌙", "银色圆盘", "月亮鱼"),
    Fish("stargazer", "观星鱼", Rarity.COMMON, False, False, 15, 35, 22, 6, "⭐", "眼睛朝上", "观星鱼"),
    Fish("flashlight_fish", "手电筒鱼", Rarity.COMMON, False, False, 5, 12, 22, 6, "🔦", "眼下发光", "手电筒鱼"),
    Fish("night_crawler", "夜行者", Rarity.COMMON, False, False, 8, 20, 0, 6, "🌑", "深夜出没", "夜行者"),
    Fish("shadow_minnow", "影子鱼", Rarity.COMMON, False, False, 3, 8, 22, 6, "👤", "几乎透明", "影子鱼"),
    Fish("midnight_loach", "午夜鳅", Rarity.COMMON, False, False, 8, 18, 0, 4, "🐛", "只在午夜", "午夜鳅"),
    Fish("dusk_perch", "黄昏鲈", Rarity.COMMON, False, False, 15, 35, 18, 22, "🐟", "黄昏时分", "黄昏鲈"),
    Fish("dawn_carp", "黎明鲤", Rarity.COMMON, False, False, 18, 40, 4, 8, "🐟", "迎接日出", "黎明鲤"),
    Fish("twilight_shrimp", "暮光虾", Rarity.COMMON, False, False, 3, 7, 18, 22, "🦐", "暮色中闪烁", "暮光虾"),
    Fish("nocturnal_goby", "夜虾虎", Rarity.COMMON, False, False, 4, 10, 22, 6, "🐟", "夜间觅食", "夜虾虎"),
    Fish("evening_tetra", "晚霞灯", Rarity.COMMON, False, False, 2, 5, 18, 22, "🐠", "橙红色", "晚霞灯"),
    Fish("night_snail", "夜螺", Rarity.COMMON, False, False, 2, 6, 22, 6, "🐚", "夜间爬行", "夜螺"),
    Fish("dark_clam", "暗蚌", Rarity.COMMON, False, False, 5, 12, 22, 6, "🐚", "黑色外壳", "暗蚌"),
    
    # 全天候鱼 (20种) 0:00-24:00
    Fish("common_carp", "普通鲤", Rarity.COMMON, False, False, 20, 50, 0, 24, "🐟", "随时可钓", "普通鲤"),
    Fish("wild_goldfish", "野生金鱼", Rarity.COMMON, False, False, 5, 12, 0, 24, "🐠", "逃逸的观赏鱼", "野生金鱼"),
    Fish("hybrid_carp", "杂交鲤", Rarity.COMMON, False, False, 25, 55, 0, 24, "🐟", "混血儿", "杂交鲤"),
    Fish("pond_fish", "池塘鱼", Rarity.COMMON, False, False, 10, 25, 0, 24, "🐟", "哪里都有", "池塘鱼"),
    Fish("river_shrimp", "河虾", Rarity.COMMON, False, False, 3, 8, 0, 24, "🦐", "全天活动", "河虾"),
    Fish("freshwater_snail", "淡水螺", Rarity.COMMON, False, False, 1, 4, 0, 24, "🐚", "慢慢爬", "淡水螺"),
    Fish("water_beetle", "水甲虫", Rarity.COMMON, False, False, 1, 3, 0, 24, "🪲", "水中昆虫", "水甲虫"),
    Fish("water_strider", "水黾", Rarity.COMMON, False, False, 1, 2, 0, 24, "🦟", "水上漂", "水黾"),
    Fish("dragonfly_larva", "蜻蜓幼虫", Rarity.COMMON, False, False, 2, 5, 0, 24, "🐛", "水虿", "蜻蜓幼虫"),
    Fish("mayfly_larva", "蜉蝣幼虫", Rarity.COMMON, False, False, 1, 3, 0, 24, "🐛", "朝生暮死", "蜉蝣幼虫"),
    Fish("caddisfly_larva", "石蛾幼虫", Rarity.COMMON, False, False, 1, 3, 0, 24, "🐛", "会造房子", "石蛾幼虫"),
    Fish("water_flea", "水蚤", Rarity.COMMON, False, False, 0.1, 0.5, 0, 24, "🔴", "红虫", "水蚤"),
    Fish("brine_shrimp", "丰年虾", Rarity.COMMON, False, False, 0.5, 1.5, 0, 24, "🦐", "鱼食", "丰年虾"),
    Fish("freshwater_mussel", "河蚬", Rarity.COMMON, False, False, 2, 6, 0, 24, "🐚", "过滤水质", "河蚬"),
    Fish("pond_turtle", "池塘龟", Rarity.COMMON, False, False, 8, 20, 0, 24, "🐢", "晒太阳", "池塘龟"),
    Fish("water_snake", "水蛇", Rarity.COMMON, False, False, 30, 80, 0, 24, "🐍", "无毒", "水蛇"),
    Fish("newt", "蝾螈", Rarity.COMMON, False, False, 8, 15, 0, 24, "🦎", "两栖动物", "蝾螈"),
    Fish("axolotl", "六角恐龙", Rarity.COMMON, False, False, 15, 30, 0, 24, "🦎", "永远的幼态", "六角恐龙"),
    Fish("water_spider", "水蜘蛛", Rarity.COMMON, False, False, 1, 2, 0, 24, "🕷️", "水下织网", "水蜘蛛"),
    Fish("leech", "水蛭", Rarity.COMMON, False, False, 3, 10, 0, 24, "🐛", "吸血鬼", "水蛭"),
]


# ========== 稀有鱼类 (30种) ==========
RARE_FISH = [
    # 白天稀有 (20种)
    Fish("koi", "锦鲤", Rarity.RARE, False, False, 20, 50, 8, 18, "🎏", "好运来", "锦鲤"),
    Fish("arowana", "金龙鱼", Rarity.RARE, False, False, 40, 80, 10, 16, "🐉", "风水鱼", "金龙鱼"),
    Fish("turtle", "乌龟", Rarity.RARE, False, False, 10, 30, 8, 18, "🐢", "长寿象征", "乌龟"),
    Fish("soft_shell_turtle", "甲鱼", Rarity.RARE, False, False, 15, 40, 8, 18, "🐢", "王八", "王八"),
    Fish("jellyfish", "水母", Rarity.RARE, False, False, 5, 20, 6, 22, "🪼", "透明飘逸", "水母"),
    Fish("seahorse", "海马", Rarity.RARE, False, False, 5, 15, 10, 18, "🦑", "爸爸生宝宝", "海马"),
    Fish("octopus", "章鱼", Rarity.RARE, False, False, 20, 60, 6, 22, "🐙", "八爪鱼", "章鱼"),
    Fish("crab", "螃蟹", Rarity.RARE, False, False, 8, 20, 8, 20, "🦀", "横着走", "螃蟹"),
    Fish("starfish", "海星", Rarity.RARE, False, False, 10, 25, 6, 18, "⭐", "五角星", "海星"),
    Fish("pufferfish", "河豚", Rarity.RARE, False, False, 15, 35, 10, 18, "🐡", "有毒但美味", "河豚"),
    Fish("flying_fish", "飞鱼", Rarity.RARE, False, False, 20, 40, 10, 16, "🐟", "会飞的鱼", "飞鱼"),
    Fish("electric_eel", "电鳗", Rarity.RARE, False, False, 50, 150, 8, 20, "⚡", "放电", "电鳗"),
    Fish("piranha", "食人鱼", Rarity.RARE, False, False, 15, 35, 10, 18, "🦷", "锋利牙齿", "食人鱼"),
    Fish("discus", "七彩神仙", Rarity.RARE, False, False, 10, 20, 10, 18, "🐠", "热带鱼之王", "七彩神仙"),
    Fish("angelfish", "神仙鱼", Rarity.RARE, False, False, 8, 15, 10, 18, "👼", "优雅", "神仙鱼"),
    Fish("betta", "斗鱼", Rarity.RARE, False, False, 5, 8, 10, 18, "🐠", "暹罗斗鱼"),
    Fish("flowerhorn", "罗汉鱼", Rarity.RARE, False, False, 15, 35, 10, 18, "🐠", "大头", "罗汉鱼"),
    Fish("oscar", "地图鱼", Rarity.RARE, False, False, 20, 40, 10, 18, "🐠", "认主人", "地图鱼"),
    Fish("pacu", "淡水白鲳", Rarity.RARE, False, False, 25, 50, 10, 18, "🐟", "素食", "淡水白鲳"),
    Fish("arapaima", "巨骨舌鱼", Rarity.RARE, False, False, 100, 250, 10, 16, "🐟", "活化石", "巨骨舌鱼"),
    
    # 夜间稀有 (10种)
    Fish("giant_salamander", "大鲵", Rarity.RARE, False, False, 50, 120, 22, 6, "🦎", "娃娃鱼", "大鲵"),
    Fish("moray_eel", "海鳗", Rarity.RARE, False, False, 60, 150, 22, 6, "🐍", "躲在洞里", "海鳗"),
    Fish("anglerfish", "鮟鱇鱼", Rarity.RARE, False, False, 20, 50, 22, 6, "🐟", "头顶灯笼", "鮟鱇鱼"),
    Fish("vampire_squid", "吸血鬼乌贼", Rarity.RARE, False, False, 15, 30, 0, 6, "🦑", "深海怪物", "吸血鬼乌贼"),
    Fish("glass_catfish", "玻璃猫", Rarity.RARE, False, False, 8, 15, 22, 6, "🐟", "透明身体", "玻璃猫"),
    Fish("ghost_knifefish", "魔鬼刀", Rarity.RARE, False, False, 30, 50, 22, 6, "🔪", "黑色幽灵", "魔鬼刀"),
    Fish("elephant_nose", "象鼻鱼", Rarity.RARE, False, False, 15, 30, 22, 6, "🐘", "长鼻子", "象鼻鱼"),
    Fish("blind_cavefish", "盲鱼", Rarity.RARE, False, False, 5, 12, 0, 24, "👁️", "没有眼睛", "盲鱼"),
    Fish("moon_jellyfish", "月亮水母", Rarity.RARE, False, False, 10, 30, 22, 6, "🌙", "夜间发光", "月亮水母"),
    Fish("bioluminescent_shrimp", "发光虾", Rarity.RARE, False, False, 3, 8, 22, 6, "✨", "自带光源", "发光虾"),
]

# ========== 史诗鱼类 (20种) ==========
EPIC_FISH = [
    Fish("whale", "小鲸鱼", Rarity.EPIC, False, False, 100, 300, 6, 22, "🐋", "海洋巨兽", "小鲸鱼"),
    Fish("shark", "鲨鱼", Rarity.EPIC, False, False, 80, 200, 10, 20, "🦈", "海中霸主", "鲨鱼"),
    Fish("dolphin", "海豚", Rarity.EPIC, False, False, 100, 250, 8, 18, "🐬", "聪明可爱", "海豚"),
    Fish("manta_ray", "蝠鲼", Rarity.EPIC, False, False, 150, 400, 8, 18, "🦅", "海中飞翔", "蝠鲼"),
    Fish("giant_squid", "大王乌贼", Rarity.EPIC, False, False, 200, 500, 22, 6, "🦑", "深海巨怪", "大王乌贼"),
    Fish("sunfish", "翻车鱼", Rarity.EPIC, False, False, 100, 300, 10, 16, "☀️", "世界最重硬骨鱼", "翻车鱼"),
    Fish("oarfish", "皇带鱼", Rarity.EPIC, False, False, 300, 800, 22, 6, "👑", "龙宫使者", "皇带鱼"),
    Fish("coelacanth", "腔棘鱼", Rarity.EPIC, False, False, 80, 180, 22, 6, "🦴", "活化石", "腔棘鱼"),
    Fish("sturgeon", "鲟鱼", Rarity.EPIC, False, False, 100, 300, 8, 18, "🐟", "鱼子酱", "鲟鱼"),
    Fish("paddlefish", "匙吻鲟", Rarity.EPIC, False, False, 80, 200, 8, 18, "🥄", "长嘴巴", "匙吻鲟"),
    Fish("gar", "雀鳝", Rarity.EPIC, False, False, 80, 200, 10, 18, "🐊", "活化石", "雀鳝"),
    Fish("bowfin", "弓鳍鱼", Rarity.EPIC, False, False, 40, 80, 10, 18, "🏹", "原始鱼类", "弓鳍鱼"),
    Fish("lungfish", "肺鱼", Rarity.EPIC, False, False, 60, 150, 8, 20, "🫁", "能呼吸空气", "肺鱼"),
    Fish("giant_catfish", "巨型鲶鱼", Rarity.EPIC, False, False, 100, 280, 22, 6, "🐡", "湄公河巨鲶", "巨型鲶鱼"),
    Fish("beluga_sturgeon", "欧鳇", Rarity.EPIC, False, False, 200, 500, 8, 18, "👸", "鱼子酱之王", "欧鳇"),
    Fish("mermaid_tear", "人鱼之泪", Rarity.EPIC, False, False, 1, 3, 0, 6, "💧", "传说中的宝物", "人鱼之泪"),
    Fish("dragon_fish", "龙鱼", Rarity.EPIC, False, False, 50, 120, 12, 16, "🐲", "东方神龙", "龙鱼"),
    Fish("phoenix_fish", "凤凰鱼", Rarity.EPIC, False, False, 30, 60, 6, 10, "🔥", "浴火重生", "凤凰鱼"),
    Fish("unicorn_fish", "独角鱼", Rarity.EPIC, False, False, 40, 80, 10, 14, "🦄", "额头有角", "独角鱼"),
    Fish("sea_serpent", "海蛇", Rarity.EPIC, False, False, 150, 400, 22, 6, "🐉", "深海巨蟒", "海蛇"),
]


# ========== 暗黑鱼类 (50种) ==========
DARK_FISH = [
    # 暗黑普通 (20种)
    Fish("dark_goldfish", "暗黑金鱼", Rarity.COMMON, True, False, 3, 8, 0, 24, "🖤", "被诅咒的金鱼"),
    Fish("cursed_carp", "诅咒鲤鱼", Rarity.COMMON, True, False, 15, 40, 0, 24, "💀", "带来厄运"),
    Fish("shadow_catfish", "暗影鲶", Rarity.COMMON, True, False, 20, 55, 0, 24, "👤", "影子般存在"),
    Fish("void_shrimp", "虚空虾", Rarity.COMMON, True, False, 2, 6, 0, 24, "🕳️", "来自虚空"),
    Fish("nightmare_snail", "噩梦螺", Rarity.COMMON, True, False, 2, 5, 0, 24, "😱", "带来噩梦"),
    Fish("corrupted_frog", "堕落蛙", Rarity.COMMON, True, False, 5, 12, 0, 24, "🐸", "黑色皮肤"),
    Fish("tainted_loach", "污染鳅", Rarity.COMMON, True, False, 8, 18, 0, 24, "☠️", "有毒"),
    Fish("dark_minnow", "暗黑鲦", Rarity.COMMON, True, False, 3, 8, 0, 24, "⚫", "成群结队"),
    Fish("shadow_goby", "影虾虎", Rarity.COMMON, True, False, 3, 10, 0, 24, "👥", "躲在阴影"),
    Fish("cursed_snail", "诅咒螺", Rarity.COMMON, True, False, 2, 5, 0, 24, "🐚", "黑色外壳"),
    Fish("dark_tadpole", "暗黑蝌蚪", Rarity.COMMON, True, False, 1, 3, 0, 24, "⬛", "永远长不大"),
    Fish("void_beetle", "虚空甲虫", Rarity.COMMON, True, False, 1, 3, 0, 24, "🪲", "吞噬光明"),
    Fish("shadow_leech", "暗影蛭", Rarity.COMMON, True, False, 3, 10, 0, 24, "🩸", "吸取生命"),
    Fish("cursed_clam", "诅咒蚌", Rarity.COMMON, True, False, 5, 15, 0, 24, "🖤", "黑珍珠"),
    Fish("dark_newt", "暗黑蝾螈", Rarity.COMMON, True, False, 8, 15, 0, 24, "🦎", "剧毒"),
    Fish("nightmare_eel", "噩梦鳗", Rarity.COMMON, True, False, 30, 80, 22, 6, "🐍", "缠绕噩梦"),
    Fish("void_crayfish", "虚空龙虾", Rarity.COMMON, True, False, 8, 15, 0, 24, "🦞", "黑色外壳"),
    Fish("shadow_perch", "暗影鲈", Rarity.COMMON, True, False, 15, 35, 0, 24, "🐟", "隐身"),
    Fish("cursed_bream", "诅咒鳊", Rarity.COMMON, True, False, 15, 35, 0, 24, "💀", "带来不幸"),
    Fish("dark_gudgeon", "暗黑麦穗", Rarity.COMMON, True, False, 3, 8, 0, 24, "⚫", "小恶魔"),
    
    # 暗黑稀有 (15种)
    Fish("shadow_eel", "暗影鳗", Rarity.RARE, True, False, 30, 80, 22, 6, "👤", "黑暗使者"),
    Fish("void_jellyfish", "虚空水母", Rarity.RARE, True, False, 5, 20, 0, 24, "🕳️", "吞噬一切"),
    Fish("cursed_turtle", "诅咒龟", Rarity.RARE, True, False, 10, 30, 0, 24, "🐢", "永生的诅咒"),
    Fish("dark_koi", "暗黑锦鲤", Rarity.RARE, True, False, 20, 50, 0, 24, "🎏", "厄运之鱼"),
    Fish("nightmare_octopus", "噩梦章鱼", Rarity.RARE, True, False, 20, 60, 22, 6, "🐙", "八条触手"),
    Fish("shadow_crab", "暗影蟹", Rarity.RARE, True, False, 8, 20, 22, 6, "🦀", "横行霸道"),
    Fish("void_seahorse", "虚空海马", Rarity.RARE, True, False, 5, 15, 0, 24, "🦑", "来自深渊"),
    Fish("cursed_puffer", "诅咒河豚", Rarity.RARE, True, False, 15, 35, 0, 24, "🐡", "剧毒"),
    Fish("dark_piranha", "暗黑食人鱼", Rarity.RARE, True, False, 15, 35, 0, 24, "🦷", "嗜血"),
    Fish("nightmare_anglerfish", "噩梦鮟鱇", Rarity.RARE, True, False, 20, 50, 22, 6, "🐟", "深渊诱惑"),
    Fish("shadow_moray", "暗影海鳗", Rarity.RARE, True, False, 60, 150, 22, 6, "🐍", "黑暗猎手"),
    Fish("void_starfish", "虚空海星", Rarity.RARE, True, False, 10, 25, 0, 24, "⭐", "五芒星"),
    Fish("cursed_discus", "诅咒神仙", Rarity.RARE, True, False, 10, 20, 0, 24, "🐠", "堕落天使"),
    Fish("dark_arowana", "暗黑龙鱼", Rarity.RARE, True, False, 40, 80, 0, 24, "🐉", "黑龙"),
    Fish("nightmare_betta", "噩梦斗鱼", Rarity.RARE, True, False, 5, 8, 0, 24, "🐠", "永恒战斗"),
    
    # 暗黑史诗 (10种)
    Fish("demon_shark", "恶魔鲨", Rarity.EPIC, True, False, 80, 200, 0, 6, "😈", "深海恶魔"),
    Fish("death_whale", "死亡之鲸", Rarity.EPIC, True, False, 100, 300, 0, 24, "☠️", "死神坐骑"),
    Fish("void_squid", "虚空乌贼", Rarity.EPIC, True, False, 200, 500, 22, 6, "🦑", "深渊领主"),
    Fish("cursed_manta", "诅咒蝠鲼", Rarity.EPIC, True, False, 150, 400, 0, 24, "🦅", "黑暗飞翔"),
    Fish("nightmare_oarfish", "噩梦皇带鱼", Rarity.EPIC, True, False, 300, 800, 22, 6, "👑", "深渊使者"),
    Fish("shadow_coelacanth", "暗影腔棘鱼", Rarity.EPIC, True, False, 80, 180, 22, 6, "🦴", "远古诅咒"),
    Fish("dark_sturgeon", "暗黑鲟鱼", Rarity.EPIC, True, False, 100, 300, 0, 24, "🐟", "黑色鱼子酱"),
    Fish("void_lungfish", "虚空肺鱼", Rarity.EPIC, True, False, 60, 150, 0, 24, "🫁", "窒息"),
    Fish("cursed_sunfish", "诅咒翻车鱼", Rarity.EPIC, True, False, 100, 300, 0, 24, "🌑", "黑日"),
    Fish("nightmare_serpent", "噩梦海蛇", Rarity.EPIC, True, False, 150, 400, 22, 6, "🐉", "深渊巨蟒"),
    
    # 暗黑传说 (5种)
    Fish("abyss_lord", "深渊领主", Rarity.LEGENDARY, True, False, 200, 500, 0, 4, "🌑", "深渊之王"),
    Fish("void_emperor", "虚空帝王", Rarity.LEGENDARY, True, False, 300, 600, 0, 6, "👑", "虚空统治者"),
    Fish("death_leviathan", "死亡利维坦", Rarity.LEGENDARY, True, False, 500, 1000, 0, 4, "💀", "海洋终结者"),
    Fish("nightmare_kraken", "噩梦克拉肯", Rarity.LEGENDARY, True, False, 400, 800, 22, 4, "🦑", "深海噩梦"),
    Fish("shadow_dragon", "暗影龙", Rarity.LEGENDARY, True, False, 300, 700, 0, 6, "🐲", "黑暗之龙"),
]


# ========== 闪光鱼类 (50种) ==========
SHINY_FISH = [
    # 闪光普通 (20种)
    Fish("shiny_goldfish", "✨小金鱼", Rarity.COMMON, False, True, 3, 8, 6, 22, "✨", "闪闪发光"),
    Fish("shiny_carp", "✨鲤鱼", Rarity.COMMON, False, True, 15, 45, 6, 20, "🌟", "金色鳞片"),
    Fish("shiny_crucian", "✨鲫鱼", Rarity.COMMON, False, True, 10, 25, 6, 20, "💫", "银光闪闪"),
    Fish("shiny_catfish", "✨鲶鱼", Rarity.COMMON, False, True, 20, 60, 6, 22, "⭐", "金色胡须"),
    Fish("shiny_shrimp", "✨河虾", Rarity.COMMON, False, True, 2, 6, 6, 20, "💎", "水晶虾"),
    Fish("shiny_crayfish", "✨小龙虾", Rarity.COMMON, False, True, 8, 15, 10, 22, "🌈", "彩虹龙虾"),
    Fish("shiny_frog", "✨青蛙", Rarity.COMMON, False, True, 5, 12, 6, 22, "💚", "翡翠蛙"),
    Fish("shiny_snail", "✨田螺", Rarity.COMMON, False, True, 2, 5, 6, 22, "🐚", "珍珠螺"),
    Fish("shiny_loach", "✨泥鳅", Rarity.COMMON, False, True, 8, 18, 6, 20, "✨", "金泥鳅"),
    Fish("shiny_perch", "✨鲈鱼", Rarity.COMMON, False, True, 20, 50, 8, 18, "🌟", "银鲈"),
    Fish("shiny_bream", "✨鳊鱼", Rarity.COMMON, False, True, 15, 35, 8, 18, "💫", "金鳊"),
    Fish("shiny_eel", "✨鳗鱼", Rarity.COMMON, False, True, 30, 80, 20, 8, "⭐", "银鳗"),
    Fish("shiny_guppy", "✨孔雀鱼", Rarity.COMMON, False, True, 2, 5, 8, 18, "🌈", "七彩孔雀"),
    Fish("shiny_tetra", "✨灯鱼", Rarity.COMMON, False, True, 2, 5, 8, 18, "💡", "超级霓虹"),
    Fish("shiny_danio", "✨斑马鱼", Rarity.COMMON, False, True, 3, 6, 8, 18, "🦓", "金斑马"),
    Fish("shiny_turtle", "✨小龟", Rarity.COMMON, False, True, 5, 15, 0, 24, "🐢", "金龟"),
    Fish("shiny_newt", "✨蝾螈", Rarity.COMMON, False, True, 8, 15, 0, 24, "🦎", "火蝾螈"),
    Fish("shiny_axolotl", "✨六角恐龙", Rarity.COMMON, False, True, 15, 30, 0, 24, "💖", "粉色恐龙"),
    Fish("shiny_clam", "✨河蚌", Rarity.COMMON, False, True, 5, 15, 6, 20, "💎", "珍珠蚌"),
    Fish("shiny_snakehead", "✨黑鱼", Rarity.COMMON, False, True, 25, 60, 8, 20, "🌟", "金黑鱼"),
    
    # 闪光稀有 (15种)
    Fish("shiny_koi", "✨锦鲤", Rarity.RARE, False, True, 20, 50, 8, 18, "🌟", "黄金锦鲤"),
    Fish("shiny_arowana", "✨金龙鱼", Rarity.RARE, False, True, 40, 80, 10, 16, "🐉", "至尊金龙"),
    Fish("shiny_jellyfish", "✨水母", Rarity.RARE, False, True, 5, 20, 6, 22, "🪼", "彩虹水母"),
    Fish("shiny_octopus", "✨章鱼", Rarity.RARE, False, True, 20, 60, 6, 22, "🐙", "金章鱼"),
    Fish("shiny_crab", "✨螃蟹", Rarity.RARE, False, True, 8, 20, 8, 20, "🦀", "黄金蟹"),
    Fish("shiny_seahorse", "✨海马", Rarity.RARE, False, True, 5, 15, 10, 18, "🦑", "金海马"),
    Fish("shiny_puffer", "✨河豚", Rarity.RARE, False, True, 15, 35, 10, 18, "🐡", "金河豚"),
    Fish("shiny_piranha", "✨食人鱼", Rarity.RARE, False, True, 15, 35, 10, 18, "🦷", "金牙鱼"),
    Fish("shiny_discus", "✨七彩神仙", Rarity.RARE, False, True, 10, 20, 10, 18, "🐠", "至尊神仙"),
    Fish("shiny_angelfish", "✨神仙鱼", Rarity.RARE, False, True, 8, 15, 10, 18, "👼", "金天使"),
    Fish("shiny_betta", "✨斗鱼", Rarity.RARE, False, True, 5, 8, 10, 18, "🐠", "金斗鱼"),
    Fish("shiny_flowerhorn", "✨罗汉鱼", Rarity.RARE, False, True, 15, 35, 10, 18, "🐠", "金罗汉"),
    Fish("shiny_electric_eel", "✨电鳗", Rarity.RARE, False, True, 50, 150, 8, 20, "⚡", "雷电鳗"),
    Fish("shiny_flying_fish", "✨飞鱼", Rarity.RARE, False, True, 20, 40, 10, 16, "🐟", "金翅飞鱼"),
    Fish("shiny_salamander", "✨大鲵", Rarity.RARE, False, True, 50, 120, 22, 6, "🦎", "金娃娃鱼"),
    
    # 闪光史诗 (10种)
    Fish("shiny_whale", "✨小鲸鱼", Rarity.EPIC, False, True, 100, 300, 6, 22, "🐋", "白金鲸"),
    Fish("shiny_shark", "✨鲨鱼", Rarity.EPIC, False, True, 80, 200, 10, 20, "🦈", "金鲨"),
    Fish("shiny_dolphin", "✨海豚", Rarity.EPIC, False, True, 100, 250, 8, 18, "🐬", "粉红海豚"),
    Fish("shiny_manta", "✨蝠鲼", Rarity.EPIC, False, True, 150, 400, 8, 18, "🦅", "金翅蝠鲼"),
    Fish("shiny_squid", "✨大王乌贼", Rarity.EPIC, False, True, 200, 500, 22, 6, "🦑", "金乌贼"),
    Fish("shiny_sunfish", "✨翻车鱼", Rarity.EPIC, False, True, 100, 300, 10, 16, "☀️", "太阳鱼"),
    Fish("shiny_oarfish", "✨皇带鱼", Rarity.EPIC, False, True, 300, 800, 22, 6, "👑", "金皇带"),
    Fish("shiny_coelacanth", "✨腔棘鱼", Rarity.EPIC, False, True, 80, 180, 22, 6, "🦴", "金化石"),
    Fish("shiny_sturgeon", "✨鲟鱼", Rarity.EPIC, False, True, 100, 300, 8, 18, "🐟", "金鲟"),
    Fish("shiny_dragon", "✨龙鱼", Rarity.EPIC, False, True, 50, 120, 12, 16, "🐲", "至尊龙鱼"),
    
    # 闪光传说 (5种)
    Fish("rainbow_fish", "彩虹鱼", Rarity.LEGENDARY, False, True, 30, 80, 12, 14, "🌈", "七色光芒"),
    Fish("golden_whale", "黄金鲸", Rarity.LEGENDARY, False, True, 100, 300, 10, 14, "👑", "海洋之王"),
    Fish("crystal_jellyfish", "水晶水母", Rarity.LEGENDARY, False, True, 5, 20, 6, 22, "💎", "透明如水晶"),
    Fish("diamond_carp", "钻石鲤", Rarity.LEGENDARY, False, True, 30, 60, 10, 14, "💎", "钻石鳞片"),
    Fish("aurora_fish", "极光鱼", Rarity.LEGENDARY, False, True, 50, 100, 0, 6, "🌌", "北极光"),
]

# ========== 汇总所有鱼类 ==========
ALL_FISH: List[Fish] = COMMON_FISH + RARE_FISH + EPIC_FISH + DARK_FISH + SHINY_FISH

# 按类型分类的字典
FISH_BY_ID = {fish.id: fish for fish in ALL_FISH}
FISH_BY_RARITY = {
    Rarity.COMMON: [f for f in ALL_FISH if f.rarity == Rarity.COMMON],
    Rarity.RARE: [f for f in ALL_FISH if f.rarity == Rarity.RARE],
    Rarity.EPIC: [f for f in ALL_FISH if f.rarity == Rarity.EPIC],
    Rarity.LEGENDARY: [f for f in ALL_FISH if f.rarity == Rarity.LEGENDARY],
}
DARK_FISH_LIST = [f for f in ALL_FISH if f.is_dark]
SHINY_FISH_LIST = [f for f in ALL_FISH if f.is_shiny]
NORMAL_FISH_LIST = [f for f in ALL_FISH if not f.is_dark and not f.is_shiny]


def get_fish_by_id(fish_id: str) -> Optional[Fish]:
    """根据ID获取鱼"""
    return FISH_BY_ID.get(fish_id)


def get_active_fish(hour: int, include_dark: bool = True, include_shiny: bool = True) -> List[Fish]:
    """获取当前时间活跃的鱼"""
    result = []
    for fish in ALL_FISH:
        if not fish.is_active(hour):
            continue
        if fish.is_dark and not include_dark:
            continue
        if fish.is_shiny and not include_shiny:
            continue
        result.append(fish)
    return result


# 验证鱼类数量
def validate_fish_data():
    """验证鱼类数据"""
    total = len(ALL_FISH)
    dark_count = len(DARK_FISH_LIST)
    shiny_count = len(SHINY_FISH_LIST)
    
    print(f"总鱼类数量: {total}")
    print(f"暗黑鱼数量: {dark_count}")
    print(f"闪光鱼数量: {shiny_count}")
    print(f"普通鱼数量: {len(COMMON_FISH)}")
    print(f"稀有鱼数量: {len(RARE_FISH)}")
    print(f"史诗鱼数量: {len(EPIC_FISH)}")
    
    # 检查ID唯一性
    ids = [f.id for f in ALL_FISH]
    if len(ids) != len(set(ids)):
        duplicates = [id for id in ids if ids.count(id) > 1]
        print(f"警告: 存在重复ID: {set(duplicates)}")
    
    return total >= 200


if __name__ == "__main__":
    validate_fish_data()
