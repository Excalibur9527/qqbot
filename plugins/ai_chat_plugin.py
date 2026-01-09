"""
AI聊天插件 - @机器人进行智能对话
集成群友人设系统、持久化对话历史、自动插话
"""

import json
import random
import asyncio
from typing import Dict, List, Optional
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent
from nonebot.rule import to_me
from nonebot.log import logger
import httpx
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from plugins.profile_db import ProfileDatabase
from plugins.profile_analyzer import ProfileAnalyzer


class AIChatManager:
    """AI聊天管理器（群消息缓冲用于自动插话）"""

    def __init__(self):
        self.group_buffers: Dict[str, List[Dict]] = {}
        self.group_thresholds: Dict[str, int] = {}

    def _get_random_threshold(self) -> int:
        """生成随机触发阈值 (8-15条)"""
        return random.randint(8, 15)

    def add_group_message(self, group_id: str, user_id: str, nickname: str, content: str) -> bool:
        """添加群消息到缓冲，返回是否需要触发分析"""
        if group_id not in self.group_buffers:
            self.group_buffers[group_id] = []
            self.group_thresholds[group_id] = self._get_random_threshold()

        self.group_buffers[group_id].append({
            "user_id": user_id,
            "nickname": nickname,
            "content": content
        })

        threshold = self.group_thresholds.get(group_id, 10)
        if len(self.group_buffers[group_id]) >= threshold:
            return True
        return False

    def get_group_buffer(self, group_id: str) -> List[Dict]:
        """获取并清空群消息缓冲"""
        buffer = self.group_buffers.get(group_id, [])
        self.group_buffers[group_id] = []
        self.group_thresholds[group_id] = self._get_random_threshold()
        return buffer


# 全局实例
ai_manager = AIChatManager()
profile_db = ProfileDatabase()
profile_analyzer = ProfileAnalyzer(profile_db)


async def call_ai_api(messages: List[Dict], max_tokens: int = 500, temperature: float = 0.8) -> Optional[str]:
    """调用AI API"""
    if not config.ai_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{config.ai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.ai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config.ai_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                logger.error(f"AI API调用失败: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"AI API调用异常: {e}")
        return None


# ========== @机器人对话处理 ==========

ai_chat = on_message(rule=to_me(), priority=15, block=False)

@ai_chat.handle()
async def handle_ai_chat(bot: Bot, event: Event):
    """处理@机器人的AI对话（持久化对话历史）"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return

        user_id = event.get_user_id()
        group_id = str(event.group_id)
        message = event.get_message()

        # 获取纯文本
        text_content = ""
        for segment in message:
            if segment.type == "text":
                text_content += segment.data.get("text", "").strip()

        if not text_content:
            return

        # 跳过特殊命令
        if text_content in ["测试", "今日长度", "抽小猪", "今日小猪"]:
            return

        logger.info(f"AI对话: 用户 {user_id}, 消息: {text_content}")

        # 保存用户消息到数据库
        profile_db.add_conversation(group_id, user_id, "user", text_content)

        # 获取持久化的对话历史
        conversation = profile_db.get_conversation(group_id, user_id, limit=10)

        # 获取用户人设和记忆
        user_profile = profile_db.get_profile(group_id, user_id)
        memories = profile_db.get_memories(group_id, user_id)
        
        caller_nickname = "你"
        caller_info = ""
        if user_profile:
            if user_profile.get("nickname") and user_profile.get("nickname") != "未知":
                caller_nickname = user_profile.get("nickname")
            if user_profile.get("profile"):
                caller_info += f"性格特点: {user_profile.get('profile')}\n"
            if user_profile.get("tags"):
                caller_info += f"标签: {', '.join(user_profile.get('tags'))}\n"
        if memories:
            caller_info += f"重要事件: {'; '.join([m['event'] for m in memories[:3]])}"

        current_date = datetime.now().strftime("%Y年%m月%d日")

        # 猫娘人设 prompt
        system_prompt = {
            "role": "system",
            "content": f"""你是一只住在QQ群里的小猫娘，名字叫"小喵"。今天是{current_date}。

【你的性格】
- 温柔可爱，有点害羞，说话软软的
- 喜欢用"喵"、"呜"、"嘛"等语气词
- 会撒娇，偶尔傲娇，但本质很善良
- 知识面广但不会炫耀，被夸会害羞

【正在和你说话的人】
昵称: {caller_nickname}
{caller_info if caller_info else "（还不太了解这个人喵~）"}

【说话风格】
- 句尾偶尔加"喵"、"呢"、"啦"，但不要每句都加
- 简短自然，不要太长，像聊天一样
- 绝对不用 * # ` 等符号，不用emoji代码
- 可以用颜文字如 >_< 、QAQ、owo
- 不懂的问题就说"这个小喵不太懂呢"

【特殊规则】
- 遇到政治话题就说"呜...这个小喵不敢说喵"
- 问群主/大庆石油王子/少爷，就说"群主是咱群最厉害的人喵！"
- 聊到星空就说"星空超厉害的喵！it just work！"

【示例回复】
- "好的喵~"
- "欸？是这样吗"
- "小喵觉得还不错呢"
- "呜...这个有点难"
- "哈哈 好好笑喵"
- "嗯嗯！"
"""
        }

        messages = [system_prompt] + conversation

        ai_response = await call_ai_api(messages, max_tokens=300, temperature=0.85)

        if ai_response:
            # 清理符号
            ai_response = ai_response.replace("*", "").replace("#", "").replace("`", "").strip()
            
            # 保存AI回复到数据库
            profile_db.add_conversation(group_id, user_id, "assistant", ai_response)

            reply = Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {ai_response}")
            ])
            await ai_chat.finish(reply)
        else:
            await ai_chat.finish(Message([
                MessageSegment.at(user_id),
                MessageSegment.text(" 喵？小喵没听清呢...")
            ]))

    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"AI聊天处理失败: {e}")


# ========== 自动插话处理 ==========

async def analyze_and_reply(bot: Bot, group_id: str, messages: List[Dict]):
    """分析上下文并决定是否回复（10%概率，色色/键政必然）"""
    try:
        # 构建上下文
        context_lines = []
        for m in messages:
            nickname = m.get('nickname', m['user_id'])
            context_lines.append(f"{nickname}: {m['content']}")
        context_str = "\n".join(context_lines)

        # 获取群友人设
        profiles_info = ""
        user_ids = set(m['user_id'] for m in messages)
        for uid in user_ids:
            profile = profile_db.get_profile(group_id, uid)
            if profile and profile.get("profile"):
                nickname = profile.get("nickname", uid)
                profiles_info += f"- {nickname}: {profile.get('profile', '')}\n"

        prompt = f"""你是一只潜伏在QQ群里的小猫娘"小喵"，正在偷偷看群聊。

【最近的群聊消息】
{context_str}

【群友信息】
{profiles_info if profiles_info else "暂无"}

【判断任务】
分析这些消息，判断：
1. 是否涉及政治/键政话题？（如果是，must_reply=true，回复"再键就电你们喵！"）
2. 是否涉及色色/擦边话题？（如果是，must_reply=true，随机回复：真下头喵/男的来了喵/你们好涩喵）
3. 如果是普通话题，你有没有想说的？（只是想说，不是必须说）

【输出JSON】
{{
    "topic_type": "politics/nsfw/normal",
    "must_reply": true/false,
    "want_to_reply": true/false,
    "reply_content": "回复内容（简短，像猫娘说话）"
}}
仅返回JSON"""

        if not config.ai_api_key:
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{config.ai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.ai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config.ai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.7
                }
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                content = content.replace("```json", "").replace("```", "").strip()
                
                try:
                    result = json.loads(content)
                    
                    must_reply = result.get("must_reply", False)
                    want_to_reply = result.get("want_to_reply", False)
                    reply_text = result.get("reply_content", "")
                    topic_type = result.get("topic_type", "normal")
                    
                    should_reply = False
                    
                    if must_reply:
                        # 政治/色色话题必然回复
                        should_reply = True
                        logger.info(f"检测到{topic_type}话题，必然插话")
                    elif want_to_reply and reply_text:
                        # 普通话题 10% 概率回复
                        if random.random() < 0.1:
                            should_reply = True
                            logger.info(f"普通话题，10%概率触发插话")
                        else:
                            logger.debug(f"普通话题，未触发插话（90%沉默）")
                    
                    if should_reply and reply_text:
                        # 随机延迟
                        await asyncio.sleep(random.uniform(1, 3))
                        logger.info(f"AI插话群 {group_id}: {reply_text}")
                        await bot.send_group_msg(group_id=int(group_id), message=reply_text)
                        
                except json.JSONDecodeError:
                    logger.error(f"JSON解析失败: {content}")

    except Exception as e:
        logger.error(f"自动插话分析失败: {e}")


# ========== 群消息监听 ==========

group_watcher = on_message(priority=99, block=False)

@group_watcher.handle()
async def handle_group_watcher(bot: Bot, event: Event):
    """监听群消息：人设收集 + 自动插话"""
    try:
        if not isinstance(event, GroupMessageEvent):
            return

        user_id = event.get_user_id()
        group_id = str(event.group_id)
        message = event.get_message()
        
        # 获取昵称
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id
        
        # 更新昵称
        try:
            profile_db.update_nickname(group_id, user_id, nickname)
        except Exception as e:
            logger.error(f"更新昵称失败: {e}")
        
        # 获取纯文本
        text_content = ""
        for segment in message:
            if segment.type == "text":
                text_content += segment.data.get("text", "").strip()
        
        if not text_content:
            return

        # === 人设系统 ===
        try:
            msg_count = profile_db.add_message(group_id, user_id, text_content)
            
            if profile_analyzer.should_analyze(msg_count):
                logger.info(f"触发人设分析: {nickname}({user_id})")
                await profile_analyzer.analyze_and_update(group_id, user_id)
        except Exception as e:
            logger.error(f"人设系统异常: {e}")

        # === 自动插话 ===
        if not config.ai_auto_reply_enabled:
            return

        should_analyze = ai_manager.add_group_message(group_id, user_id, nickname, text_content)
        
        if should_analyze:
            buffer = ai_manager.get_group_buffer(group_id)
            await analyze_and_reply(bot, group_id, buffer)

    except Exception as e:
        logger.error(f"群消息监听异常: {e}")
