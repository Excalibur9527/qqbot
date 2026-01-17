"""
今日词云插件
功能：统计今日群聊热点词，生成词云
命令：/今日词云
统计时间：0点开始，8点更新
"""

import json
import re
from collections import Counter
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Set
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent, Message, MessageSegment
from nonebot.log import logger

from plugins.unified_db import unified_db


# 停用词列表（过滤无意义的词）
STOP_WORDS = {
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到",
    "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "啊", "吗", "呢", "吧", "哦",
    "嗯", "哈", "呀", "喔", "哟", "嘿", "嘛", "啦", "咯", "喵", "呜", "嘛", "么", "吗", "呢", "吧", "啊",
    "/", "、", "，", "。", "！", "？", "：", "；", """, """, "'", "'", "（", "）", "[", "]", "{", "}", 
    "【", "】", "《", "》", "—", "…", "·", "~", "@", "#", "$", "%", "^", "&", "*", "+", "=", "|", "\\",
}


class WordCloudManager:
    """词云管理器"""
    
    def __init__(self):
        self.data_dir = Path("data/wordcloud")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.group_messages: Dict[str, List[str]] = {}  # {group_id: [messages]}
        self.group_dates: Dict[str, str] = {}  # {group_id: date}
        self.group_wordclouds: Dict[str, Dict] = {}  # {group_id: {words, generated_at}}
    
    def add_message(self, group_id: str, text: str):
        """添加消息到缓冲"""
        today = str(date.today())
        
        # 检查是否需要重置（新的一天）
        if group_id not in self.group_dates or self.group_dates[group_id] != today:
            self.group_messages[group_id] = []
            self.group_dates[group_id] = today
            # 清除旧的词云
            if group_id in self.group_wordclouds:
                del self.group_wordclouds[group_id]
        
        # 添加消息
        if group_id not in self.group_messages:
            self.group_messages[group_id] = []
        self.group_messages[group_id].append(text)
    
    def extract_words(self, text: str) -> List[str]:
        """提取词语（简单的中文分词）"""
        # 移除特殊字符和数字
        text = re.sub(r'[0-9a-zA-Z\s]+', ' ', text)
        
        # 简单的中文分词：提取2-4个字的词组
        words = []
        
        # 提取2字词
        for i in range(len(text) - 1):
            word = text[i:i+2]
            if len(word) == 2 and word not in STOP_WORDS:
                words.append(word)
        
        # 提取3字词
        for i in range(len(text) - 2):
            word = text[i:i+3]
            if len(word) == 3 and word not in STOP_WORDS:
                words.append(word)
        
        # 提取4字词
        for i in range(len(text) - 3):
            word = text[i:i+4]
            if len(word) == 4 and word not in STOP_WORDS:
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
            words = self.extract_words(msg)
            all_words.extend(words)
        
        # 统计词频
        word_counter = Counter(all_words)
        
        # 获取前30个高频词
        top_words = word_counter.most_common(30)
        
        result = {
            "words": [{"word": w, "count": c} for w, c in top_words],
            "count": len(messages),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                        return False  # 今天已经生成过
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
        lines = ["📊 今日词云 📊"]
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
