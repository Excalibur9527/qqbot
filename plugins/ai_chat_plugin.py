"""
AI聊天插件 - @机器人进行智能对话
集成群友人设系统、持久化对话历史、自动插话、LLM敏感内容检测
"""

import json
import random
import asyncio
from pathlib import Path
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
from plugins.unified_db import unified_db
from plugins.profile_analyzer import ProfileAnalyzer


def get_unified_db():
    """获取统一数据库实例"""
    return unified_db

# 特殊图片路径
SPECIAL_IMG_DIR = Path(__file__).parent.parent / "resources" / "pig" / "special"


def get_special_image(img_name: str) -> Optional[bytes]:
    """获取特殊图片的字节数据"""
    img_path = SPECIAL_IMG_DIR / img_name
    if img_path.exists():
        try:
            return img_path.read_bytes()
        except Exception as e:
            logger.error(f"读取特殊图片失败 {img_name}: {e}")
    return None


class AIChatManager:
    """AI聊天管理器（群消息缓冲用于敏感词检测和自动插话）"""

    def __init__(self):
        self.group_buffers: Dict[str, List[Dict]] = {}
        self.analyze_threshold = 8  # 每8条消息触发一次LLM分析

    def add_group_message(self, group_id: str, user_id: str, nickname: str, content: str) -> bool:
        """添加群消息到缓冲，返回是否需要触发分析"""
        if group_id not in self.group_buffers:
            self.group_buffers[group_id] = []

        self.group_buffers[group_id].append({
            "user_id": user_id,
            "nickname": nickname,
            "content": content
        })

        if len(self.group_buffers[group_id]) >= self.analyze_threshold:
            return True
        return False

    def get_group_buffer(self, group_id: str) -> List[Dict]:
        """获取并清空群消息缓冲"""
        buffer = self.group_buffers.get(group_id, [])
        self.group_buffers[group_id] = []
        return buffer


# 全局实例
ai_manager = AIChatManager()
profile_analyzer = ProfileAnalyzer(unified_db)


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


async def check_single_message_sensitive(text: str) -> Optional[Dict]:
    """
    使用LLM检测单条消息是否敏感
    返回: {"type": "sexist/nsfw/muslim/politics/rude/normal", "reason": "原因"} 或 None
    """
    if not config.ai_api_key:
        return None
    
    prompt = f"""判断这条消息是否包含敏感内容：

"{text}"

【敏感类型】
- sexist: 性别歧视、厌男厌女（如"男的真是"、"普信男"）
- nsfw: 色情擦边（如"色色"、"ghs"、"好涩"）
- muslim: 涉及回民/清真的敏感言论
- politics: 政治敏感、键政
- rude: 粗鲁辱骂（如"傻逼"、"nmsl"）
- normal: 正常内容

【输出JSON】
{{"type": "类型", "reason": "简短原因"}}
仅返回JSON"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{config.ai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.ai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config.ai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.1
                }
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(content)
    except Exception as e:
        logger.error(f"单条敏感词检测异常: {e}")
    
    return None


async def analyze_messages_with_llm(bot: Bot, group_id: str, messages: List[Dict]):
    """
    使用LLM分析8条消息，检测敏感内容并决定是否回复
    敏感类型: sexist(性别歧视), nsfw(色色), muslim(回民相关), politics(键政), rude(粗鲁)
    """
    if not config.ai_api_key:
        return
    
    # 构建消息列表
    msg_lines = []
    for i, m in enumerate(messages, 1):
        msg_lines.append(f"{i}. {m['nickname']}: {m['content']}")
    messages_text = "\n".join(msg_lines)
    
    prompt = f"""你是群聊内容审核员。分析以下8条群聊消息，逐一判断每条是否包含敏感内容。

【群聊消息】
{messages_text}

【敏感类型定义】
- sexist: 性别歧视、厌男厌女言论（如"男的真是"、"女人都"、"普信男"等）
- nsfw: 色情擦边、开车言论（如"色色"、"ghs"、"好涩"等）
- muslim: 涉及回民/清真/伊斯兰的敏感言论
- politics: 政治敏感、键政言论（涉及领导人、政党、敏感事件等）
- rude: 对他人粗鲁辱骂（如"傻逼"、"nmsl"等脏话）
- normal: 正常内容

【输出JSON格式】
{{
    "results": [
        {{"index": 1, "type": "normal", "reason": ""}},
        {{"index": 2, "type": "nsfw", "reason": "提到色色"}},
        ...
    ],
    "should_reply": true/false,
    "reply_content": "如果要回复，写一句猫娘风格的吐槽（简短）",
    "reply_target_index": 0
}}

规则：
1. 每条消息都要判断，共8条
2. 只有检测到敏感内容才 should_reply=true
3. reply_target_index 是要回复的那条消息的序号（1-8）
4. 正常聊天不要回复，只有敏感内容才回复
5. 仅返回JSON，不要markdown"""

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
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0.3
                }
            )

            if response.status_code != 200:
                logger.error(f"LLM敏感词检测失败: {response.status_code}")
                return

            content = response.json()["choices"][0]["message"]["content"]
            content = content.replace("```json", "").replace("```", "").strip()
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"LLM返回JSON解析失败: {content}")
                return
            
            # 处理检测结果，扣减功德
            results = result.get("results", [])
            for r in results:
                idx = r.get("index", 0) - 1
                sensitive_type = r.get("type", "normal")
                
                if sensitive_type != "normal" and 0 <= idx < len(messages):
                    m = messages[idx]
                    user_id = m["user_id"]
                    nickname = m["nickname"]
                    
                    # 扣减功德
                    try:
                        db = get_unified_db()
                        today_merit, total_merit = db.deduct_merit(group_id, user_id, nickname, 10)
                        logger.info(f"LLM检测扣功德: {nickname}({user_id}) 类型={sensitive_type}, 当前功德={total_merit}")
                    except Exception as e:
                        logger.error(f"扣减功德失败: {e}")
            
            # 发送回复
            should_reply = result.get("should_reply", False)
            reply_content = result.get("reply_content", "")
            target_idx = result.get("reply_target_index", 0) - 1
            
            if should_reply and reply_content:
                # 找到要回复的敏感类型
                sensitive_type = "normal"
                for r in results:
                    if r.get("index", 0) - 1 == target_idx:
                        sensitive_type = r.get("type", "normal")
                        break
                
                # 构建回复消息
                msg = Message()
                img_bytes = None
                
                if sensitive_type == "sexist":
                    img_bytes = get_special_image("有股味(有猪味).jpg")
                elif sensitive_type == "nsfw":
                    img_bytes = get_special_image("猪出警.jpg")
                elif sensitive_type == "muslim":
                    img_name = random.choice(["猪吃回民.jpg", "猪降临(清真).jpg"])
                    img_bytes = get_special_image(img_name)
                elif sensitive_type == "rude":
                    img_bytes = get_special_image("猪币.jpg")
                
                if img_bytes:
                    msg.append(MessageSegment.image(img_bytes))
                msg.append(MessageSegment.text(reply_content))
                
                # 随机延迟后发送
                await asyncio.sleep(random.uniform(0.5, 2.0))
                await bot.send_group_msg(group_id=int(group_id), message=msg)
                logger.info(f"LLM敏感词回复群 {group_id}: {reply_content}")

    except Exception as e:
        logger.error(f"LLM敏感词分析异常: {e}")


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

        # 获取昵称
        sender = event.sender
        nickname = sender.card if sender.card else sender.nickname
        if not nickname:
            nickname = user_id

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

        # === LLM敏感词检测 ===
        sensitive_result = await check_single_message_sensitive(text_content)
        if sensitive_result and sensitive_result.get("type") != "normal":
            sensitive_type = sensitive_result.get("type", "")
            reason = sensitive_result.get("reason", "")
            logger.info(f"@机器人检测到敏感内容: {sensitive_type} - {reason}")
            
            # 扣减功德
            try:
                db = get_unified_db()
                today_merit, total_merit = db.deduct_merit(group_id, user_id, nickname, 10)
                logger.info(f"扣功德: {nickname}({user_id}) 类型={sensitive_type}, 当前功德={total_merit}")
            except Exception as e:
                logger.error(f"扣减功德失败: {e}")
                total_merit = "?"
            
            # 构建回复
            msg = Message()
            msg.append(MessageSegment.at(user_id))
            msg.append(MessageSegment.text(" "))
            
            img_bytes = None
            reply_text = ""
            
            if sensitive_type == "sexist":
                img_bytes = get_special_image("有股味(有猪味).jpg")
                reply_text = random.choice(["有股味了喵", "男的来了喵", "这话有点..."])
            elif sensitive_type == "nsfw":
                img_bytes = get_special_image("猪出警.jpg")
                reply_text = "不可以涩涩喵！"
            elif sensitive_type == "muslim":
                img_name = random.choice(["猪吃回民.jpg", "猪降临(清真).jpg"])
                img_bytes = get_special_image(img_name)
                reply_text = random.choice(["猪来咯~", "清真警告喵"])
            elif sensitive_type == "politics":
                reply_text = "呜...这个小喵不敢说喵"
            elif sensitive_type == "rude":
                img_bytes = get_special_image("猪币.jpg")
                reply_text = random.choice(["小喵不理你了！", "哼！", "好凶喵..."])
            
            if img_bytes:
                msg.append(MessageSegment.image(img_bytes))
            msg.append(MessageSegment.text(f"{reply_text}\n功德 -10 (当前: {total_merit})"))
            
            await ai_chat.finish(msg)
            return

        # 保存用户消息到数据库
        db = get_unified_db()
        db.add_conversation(group_id, user_id, "user", text_content)

        # 获取持久化的对话历史
        conversation = db.get_conversation(group_id, user_id, limit=10)

        # 获取用户完整数据（功德、头衔、图鉴等）
        user_data = db.get_or_create_user(group_id, user_id, nickname)
        memories = db.get_memories(group_id, user_id)
        collection_count = db.get_collection_count(group_id, user_id)
        
        # 构建用户信息
        caller_nickname = nickname if nickname else "你"
        caller_info = ""
        
        # 人设信息
        if user_data.profile:
            caller_info += f"性格特点: {user_data.profile}\n"
        if user_data.tags:
            caller_info += f"标签: {', '.join(user_data.tags)}\n"
        
        # 功德信息
        merit_desc = ""
        if user_data.total_merit >= 10000:
            merit_desc = "功德圆满的大师"
        elif user_data.total_merit >= 5000:
            merit_desc = "修行高深"
        elif user_data.total_merit >= 1000:
            merit_desc = "虔诚的修行者"
        elif user_data.total_merit >= 100:
            merit_desc = "初入修行"
        elif user_data.total_merit < 0:
            merit_desc = "功德有亏"
        
        if merit_desc:
            caller_info += f"修行状态: {merit_desc}（功德{user_data.total_merit}）\n"
        
        # 头衔信息
        if user_data.current_title:
            caller_info += f"头衔: {user_data.current_title}\n"
        
        # 钓鱼信息
        if collection_count > 0:
            if collection_count >= 200:
                fish_desc = "传说中的赛博鱼王"
            elif collection_count >= 100:
                fish_desc = "资深钓鱼佬"
            elif collection_count >= 50:
                fish_desc = "钓鱼爱好者"
            else:
                fish_desc = f"钓鱼新手（图鉴{collection_count}/200）"
            caller_info += f"钓鱼: {fish_desc}\n"
        
        # 记忆
        if memories:
            caller_info += f"重要事件: {'; '.join([m['event'] for m in memories[:3]])}"
        
        # 根据头衔调整称呼方式
        title_greeting = ""
        if user_data.current_title:
            title_map = {
                "赛博如来": "大师",
                "机械飞升": "前辈",
                "赛博罗汉": "施主",
                "量子菩萨": "菩萨",
                "电子居士": "居士",
                "赛博鱼王": "鱼王大人",
                "钓鱼佬": "钓鱼大师"
            }
            title_greeting = title_map.get(user_data.current_title, "")

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
昵称: {caller_nickname}{f'（{title_greeting}）' if title_greeting else ''}
{caller_info if caller_info else "（还不太了解这个人喵~）"}

【说话风格】
- 句尾偶尔加"喵"、"呢"、"啦"，但不要每句都加
- 简短自然，不要太长，像聊天一样
- 绝对不用 * # ` 等符号，不用emoji代码
- 可以用颜文字如 >_< 、QAQ、owo
- 不懂的问题就说"这个小喵不太懂呢"
{f'- 对方是{title_greeting}，要尊敬一点喵' if title_greeting else ''}

【特殊规则】
- 遇到政治话题就说"呜...这个小喵不敢说喵"
- 问群主/大庆石油王子/少爷，就说"群主是咱群最厉害的人喵！"
- 聊到星空就说"星空超厉害的喵！it just work！"
- 如果对方功德很高，要表示敬佩
- 如果对方是钓鱼大师，可以聊聊钓鱼的话题

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
            db.add_conversation(group_id, user_id, "assistant", ai_response)

            reply = Message([
                MessageSegment.at(user_id),
                MessageSegment.text(f" {ai_response}")
            ])
            await ai_chat.finish(reply)
        else:
            # AI无法回答时，发送"不猪道"图片
            img_bytes = get_special_image("不猪道.jpg")
            msg = Message([
                MessageSegment.at(user_id),
                MessageSegment.text(" ")
            ])
            if img_bytes:
                msg.append(MessageSegment.image(img_bytes))
            msg.append(MessageSegment.text("小喵不猪道呢..."))
            await ai_chat.finish(msg)

    except Exception as e:
        if "FinishedException" in str(type(e)):
            return
        logger.error(f"AI聊天处理失败: {e}")


# ========== 群消息监听 ==========

group_watcher = on_message(priority=99, block=False)

@group_watcher.handle()
async def handle_group_watcher(bot: Bot, event: Event):
    """监听群消息：人设收集 + 每8条消息LLM敏感词检测"""
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
            db = get_unified_db()
            db.update_nickname(group_id, user_id, nickname)
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
            msg_count = db.add_message(group_id, user_id, text_content)
            
            if profile_analyzer.should_analyze(msg_count):
                logger.info(f"触发人设分析: {nickname}({user_id})")
                await profile_analyzer.analyze_and_update(group_id, user_id)
        except Exception as e:
            logger.error(f"人设系统异常: {e}")

        # === 每8条消息触发LLM敏感词检测 ===
        should_analyze = ai_manager.add_group_message(group_id, user_id, nickname, text_content)
        
        if should_analyze:
            buffer = ai_manager.get_group_buffer(group_id)
            logger.info(f"触发LLM敏感词检测，群 {group_id}，消息数: {len(buffer)}")
            await analyze_messages_with_llm(bot, group_id, buffer)

    except Exception as e:
        logger.error(f"群消息监听异常: {e}")
