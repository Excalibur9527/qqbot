"""
今日词云插件
功能：统计今日群聊热点词，生成词云
命令：/今日词云
统计时间：0点开始，8点更新
使用jieba分词 + 多层过滤机制
"""

import re
from collections import Counter
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Set
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent, Message, MessageSegment
from nonebot.log import logger

try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba未安装，词云功能将使用简单分词")


# ========== 停用词库 ==========

# 基础停用词（虚词、代词、连词等）
BASIC_STOP_WORDS = {
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到",
    "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "他", "她", "它", "我们",
    "你们", "他们", "这个", "那个", "这些", "那些", "这样", "那样", "怎么", "什么", "哪里", "为什么",
    "因为", "所以", "但是", "然后", "如果", "虽然", "可是", "而且", "或者", "还是", "不过", "只是",
    "已经", "还", "再", "又", "才", "就", "都", "只", "也", "还是", "更", "最", "非常", "十分", "特别",
    "比较", "有点", "一点", "一些", "许多", "很多", "一直", "总是", "经常", "有时", "偶尔", "从来",
    "能", "会", "可以", "应该", "必须", "需要", "想", "要", "得", "过", "来", "去", "给", "被", "把",
    "让", "叫", "使", "由", "对", "向", "从", "以", "为", "于", "与", "及", "而", "或", "且", "则",
}

# 语气词（重点过滤）
MODAL_WORDS = {
    "啊", "呀", "哇", "呢", "吧", "嘛", "咯", "喽", "哦", "哟", "嘿", "嗨", "哈", "呵", "嘻", "嘿嘿",
    "哈哈", "呵呵", "嘻嘻", "嘿嘿", "啦", "哪", "呐", "嘞", "喔", "唷", "哎", "哎呀", "哎哟", "唉",
    "嗯", "嗯嗯", "嘛", "么", "嘞", "咧", "喵", "呜", "呜呜", "嘤", "嘤嘤", "嘶", "嘶嘶", "嘿咻",
    "哼", "哼哼", "嗷", "嗷嗷", "嗷呜", "呃", "额", "emm", "emmm", "ummm", "嗷呜", "嗯哼", "嗯呐",
}

# 网络用语/表情词
INTERNET_SLANG = {
    "哈哈哈", "哈哈哈哈", "哈哈哈哈哈", "嘿嘿嘿", "嘻嘻嘻", "呵呵呵", "嘤嘤嘤", "呜呜呜", "嘤嘤嘤嘤",
    "草", "草草草", "卧槽", "我去", "我靠", "牛逼", "牛批", "厉害", "666", "233", "2333", "23333",
    "hhh", "hhhh", "hhhhh", "www", "wwww", "wwwww", "orz", "OTZ", "囧", "囧rz",
}

# 无意义单字（只过滤单字，词组中的不过滤）
MEANINGLESS_SINGLE = {
    "个", "些", "样", "种", "次", "下", "点", "会", "能", "要", "想", "看", "说", "做", "去", "来",
    "给", "对", "把", "被", "让", "叫", "用", "从", "在", "到", "向", "往", "由", "为", "以", "及",
}

# 特殊符号和标点
PUNCTUATION = {
    "/", "、", "，", "。", "！", "？", "：", "；", """, """, "'", "'", "（", "）", "[", "]", "{", "}", 
    "【", "】", "《", "》", "—", "…", "·", "~", "@", "#", "$", "%", "^", "&", "*", "+", "=", "|", "\\",
    "<", ">", ".", ",", "!", "?", ":", ";", "'", '"', "(", ")", "-", "_", "`", "、", "，", "。",
}

# 合并所有停用词
ALL_STOP_WORDS = BASIC_STOP_WORDS | MODAL_WORDS | INTERNET_SLANG | PUNCTUATION

# 保留的词性（jieba分词用）
KEEP_POS = {
    'n',   # 名词
    'nr',  # 人名
    'ns',  # 地名
    'nt',  # 机构名
    'nz',  # 其他专名
    'v',   # 动词
    'vn',  # 名动词
    'a',   # 形容词
    'an',  # 名形词
    'i',   # 成语
    'l',   # 习用语
    'eng', # 英文
}

# 自定义词典（群聊常见词组）
CUSTOM_WORDS = [
    "钓鱼", "敲木鱼", "木鱼", "功德", "小猪", "塔罗牌", "占卜", "运势", "今日长度",
    "俄罗斯轮盘", "轮盘", "词云", "人设", "小喵", "猫娘", "群友", "机器人",
    "打工人", "社畜", "摸鱼", "划水", "内卷", "躺平", "emo", "破防", "绷不住",
]


class WordCloudManager:
    """词云管理器 - 优化版"""
    
    def __init__(self):
        self.data_dir = Path("data/wordcloud")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.group_messages: Dict[str, List[str]] = {}
        self.group_dates: Dict[str, str] = {}
        self.group_wordclouds: Dict[str, Dict] = {}
        
        # 初始化jieba
        if JIEBA_AVAILABLE:
            # 添加自定义词典
            for word in CUSTOM_WORDS:
                jieba.add_word(word)
            logger.info("jieba分词初始化完成，已加载自定义词典")
    
    def add_message(self, group_id: str, text: str):
        """添加消息到缓冲"""
        today = str(date.today())
        
        # 检查是否需要重置（新的一天）
        if group_id not in self.group_dates or self.group_dates[group_id] != today:
            self.group_messages[group_id] = []
            self.group_dates[group_id] = today
            if group_id in self.group_wordclouds:
                del self.group_wordclouds[group_id]
        
        # 添加消息
        if group_id not in self.group_messages:
            self.group_messages[group_id] = []
        self.group_messages[group_id].append(text)
    
    def extract_words_jieba(self, text: str) -> List[str]:
        """使用jieba分词提取词语（推荐）"""
        words = []
        
        # 使用词性标注分词
        word_pairs = pseg.cut(text)
        
        for word, pos in word_pairs:
            # 多层过滤
            # 1. 过滤停用词
            if word in ALL_STOP_WORDS:
                continue
            
            # 2. 过滤单字无意义词
            if len(word) == 1 and word in MEANINGLESS_SINGLE:
                continue
            
            # 3. 只保留2-4字的词
            if len(word) < 2 or len(word) > 4:
                continue
            
            # 4. 词性过滤（只保留有意义的词性）
            if pos not in KEEP_POS:
                continue
            
            # 5. 过滤纯数字和纯英文
            if word.isdigit() or word.isalpha():
                continue
            
            words.append(word)
        
        return words
    
    def extract_words_simple(self, text: str) -> List[str]:
        """简单分词（jieba不可用时的备用方案）"""
        # 移除特殊字符和数字
        text = re.sub(r'[0-9a-zA-Z\s]+', ' ', text)
        
        words = []
        
        # 提取2-4字词组
        for length in [2, 3, 4]:
            for i in range(len(text) - length + 1):
                word = text[i:i+length]
                if len(word) == length and word not in ALL_STOP_WORDS:
                    words.append(word)
        
        return words
    
    def generate_wordcloud(self, group_id: str) -> Dict:
        """生成词云数据"""
        if group_id not in self.group_messages:
            return {"words": [], "count": 0, "generated_at": ""}
        
        messages = self.group_messages[group_id]
        if not messages:
            return {"words": [], "count": 0, "generated_at": ""}
        
        # 提取所有词语
        all_words = []
        for msg in messages:
            if JIEBA_AVAILABLE:
                words = self.extract_words_jieba(msg)
            else:
                words = self.extract_words_simple(msg)
            all_words.extend(words)
        
        # 统计词频
        word_counter = Counter(all_words)
        
        # 获取前30个高频词
        top_words = word_counter.most_common(30)
        
        result = {
            "words": [{"word": w, "count": c} for w, c in top_words],
            "count": len(messages),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "jieba" if JIEBA_AVAILABLE else "simple"
        }
        
        # 缓存词云
        self.group_wordclouds[group_id] = result
        
        return result
    
    def should_update_wordcloud(self, group_id: str) -> bool:
        """检查是否应该更新词云（8点后）"""
        current_hour = datetime.now().hour
        
        # 8点之前不更新
        if current_hour < 8:
            return False
        
        # 检查今天是否已经生成过
        if group_id in self.group_wordclouds:
            generated_at = self.group_wordclouds[group_id].get("generated_at", "")
            if generated_at:
                try:
                    gen_date = datetime.strptime(generated_at, "%Y-%m-%d %H:%M:%S").date()
                    if gen_date == date.today():
                        return False
                except:
                    pass
        
        return True
    
    def get_wordcloud(self, group_id: str) -> Dict:
        """获取词云（如果需要则生成）"""
        if self.should_update_wordcloud(group_id):
            return self.generate_wordcloud(group_id)
        elif group_id in self.group_wordclouds:
            return self.group_wordclouds[group_id]
        else:
            return {"words": [], "count": 0, "generated_at": ""}


# 全局实例
wordcloud_manager = WordCloudManager()


# 注册命令
wordcloud_cmd = on_command("今日词云", aliases={"词云", "热词"}, priority=5, block=True)


@wordcloud_cmd.handle()
async def handle_wordcloud(bot: Bot, event: Event):
    """处理今日词云命令"""
    try:
        if not isinstance(event, GroupMessageEvent):
            await wordcloud_cmd.finish("请在群里使用喵~")
            return
        
        group_id = str(event.group_id)
        current_hour = datetime.now().hour
        
        # 8点之前提示
        if current_hour < 8:
            await wordcloud_cmd.finish("词云还在生成中喵~ 请8点后再来看吧！")
            return
        
        # 获取词云
        wordcloud_data = wordcloud_manager.get_wordcloud(group_id)
        
        if not wordcloud_data["words"]:
            await wordcloud_cmd.finish("今天还没有足够的聊天记录喵~")
            return
        
        # 格式化输出
        method_text = "智能分词" if wordcloud_data.get("method") == "jieba" else "简单分词"
        lines = [f"📊 今日词云 ({method_text}) 📊"]
        lines.append(f"统计消息: {wordcloud_data['count']} 条")
        lines.append(f"生成时间: {wordcloud_data['generated_at']}")
        lines.append("")
        lines.append("🔥 热门词汇 TOP 20:")
        
        for i, item in enumerate(wordcloud_data["words"][:20], 1):
            word = item["word"]
            count = item["count"]
            # 根据排名显示不同的emoji
            if i <= 3:
                emoji = ["🥇", "🥈", "🥉"][i-1]
            else:
                emoji = f"{i}."
            lines.append(f"{emoji} {word} ({count}次)")
        
        await wordcloud_cmd.finish("\n".join(lines))
        
    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"词云生成异常: {e}")


# 导出给其他模块使用
def add_message_to_wordcloud(group_id: str, text: str):
    """添加消息到词云统计"""
    wordcloud_manager.add_message(group_id, text)
