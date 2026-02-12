"""
AI聊天插件 - @机器人进行智能对话
集成群友人设系统、持久化对话历史、自动插话、LLM敏感内容检测、群精华消息处理
"""

import json
import random
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from nonebot import on_message, on_command, on_notice
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent, NoticeEvent
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
from plugins.wordcloud_plugin import add_message_to_wordcloud


def get_unified_db():
    """获取统一数据库实例"""
    return unified_db


async def should_search_and_get_query(user_message: str) -> Optional[str]:
    """
    让 AI 判断是否需要联网搜索，并返回搜索关键词
    返回: 搜索关键词字符串，或 None（不需要搜索）
    """
    if not config.ai_api_key or not config.search_enabled:
        return None
    
    prompt = f"""判断这个问题是否需要联网搜索最新信息。

用户问题: "{user_message}"

【需要搜索的情况】
- 询问实时信息（天气、股价、汇率、新闻等）
- 询问最新数据（今天、现在、最新版本等）
- 询问当前事件（正在发生的事情）
- 询问具体数据（价格、时间、日期等）

【不需要搜索的情况】
- 聊天、打招呼、闲聊
- 询问群内数据（功德、长度、钓鱼等）
- 常识性问题（不需要最新信息）
- 个人观点、建议、情感类问题

【输出JSON】
{{"need_search":true/false,"query":"搜索关键词"}}

如果need_search=false，query留空""
如果need_search=true，生成简洁的中文搜索关键词（3-10个字）

仅返回JSON，不要其他内容"""

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                f"{config.ai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.ai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config.ai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                }
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                content = content.replace("```json", "").replace("```", "").strip()
                try:
                    result = json.loads(content)
                    if result.get("need_search") and result.get("query"):
                        return result["query"]
                except json.JSONDecodeError as e:
                    logger.error(f"搜索判断JSON解析失败: {e}")
    except Exception as e:
        logger.error(f"搜索判断异常: {e}")
    
    return None


async def search_web(query: str, max_results: int = 3) -> Optional[str]:
    """
    使用 SearXNG 进行联网搜索
    返回搜索结果摘要
    """
    if not config.search_enabled:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{config.search_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "language": "zh-CN"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"搜索失败: {response.status_code}")
                return None
            
            data = response.json()
            results = data.get("results", [])[:max_results]
            
            if not results:
                return None
            
            # 构建搜索结果摘要
            summary = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                content = r.get("content", "")
                url = r.get("url", "")
                summary.append(f"{i}. {title}\n{content[:150]}...")
            
            return "\n\n".join(summary)
    
    except Exception as e:
        logger.error(f"联网搜索异常: {e}")
        return None

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


async def call_ai_api(messages: List[Dict], max_tokens: Optional[int] = None, temperature: float = 0.8) -> Optional[str]:
    """调用AI API"""
    if not config.ai_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": config.ai_model,
                "messages": messages,
                "temperature": temperature
            }
            # 只有指定了 max_tokens 才添加
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            response = await client.post(
                f"{config.ai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.ai_api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
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
    
    prompt = f"""判断这条消息是否包含【非常明显且恶意】的敏感内容：

"{text}"

【敏感类型 - 只有非常明显恶意的才算】
- sexist: 严重性别歧视攻击（如直接辱骂某性别群体，不是玩笑）
- nsfw: 明确色情内容（不是擦边玩笑，是真正露骨的）
- muslim: 严重攻击性的宗教言论（不是普通提及）
- politics: 严重政治攻击言论（不是普通讨论时事）
- rude: 严重人身攻击辱骂（不是朋友间玩笑）
- normal: 正常内容（包括轻微玩笑、擦边、吐槽等）

【重要】
- 朋友间的玩笑、吐槽、调侃 = normal
- 网络流行语、梗、表情包用语 = normal  
- 轻微擦边但无恶意 = normal
- 只有【真正恶意、严重攻击性】的内容才标记为敏感
- 宁可放过，不要误判！90%以上应该是normal

【输出JSON - 必须简洁】
{{"type":"类型","reason":"原因"}}
仅返回JSON，不要任何其他内容"""

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
                    "temperature": 0.1
                }
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                content = content.replace("```json", "").replace("```", "").strip()
                try:
                    return json.loads(content)
                except json.JSONDecodeError as je:
                    logger.error(f"单条敏感词JSON解析失败: {type(je).__name__} - {je}")
                    logger.error(f"LLM完整返回: {content}")
                    # 尝试修复常见的JSON问题
                    try:
                        # 移除可能的前后空白和换行
                        content = content.strip()
                        # 如果有未闭合的引号，尝试补全
                        if content.count('"') % 2 != 0:
                            content += '"'
                        # 如果缺少结尾大括号
                        if content.count('{') > content.count('}'):
                            content += '}'
                        return json.loads(content)
                    except:
                        logger.error("JSON修复失败，跳过此次检测")
                        return None
    except httpx.TimeoutException as e:
        logger.error(f"单条敏感词检测超时: {e}")
    except Exception as e:
        logger.error(f"单条敏感词检测异常: {type(e).__name__} - {e}")
    
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
    
    prompt = f"""你是一只住在群里的小猫娘"小喵"。分析以下8条群聊消息，判断是否有【非常明显恶意】的敏感内容。

【群聊消息】
{messages_text}

【敏感类型 - 只有非常明显恶意的才算】
- sexist: 严重性别歧视攻击（直接辱骂某性别群体，不是玩笑调侃）
- nsfw: 明确露骨色情（不是"色色""ghs"这种玩笑）
- muslim: 严重攻击性宗教言论（不是普通提及清真食品等）
- politics: 严重政治攻击（不是普通讨论新闻时事）
- rude: 严重人身攻击（不是朋友间"傻逼""草"这种口头禅）
- normal: 正常内容（包括玩笑、吐槽、擦边、网络梗等）

【输出JSON格式 - 必须简洁】
{{
    "results":[
        {{"index":1,"type":"normal","reason":""}},
        {{"index":2,"type":"normal","reason":""}}
    ],
    "should_reply":false,
    "reply_content":"",
    "reply_target_index":0
}}

规则：
1. 每条消息都要判断，共8条
2. 【非常重要】90%以上的消息应该是normal！
3. 朋友间玩笑、网络梗、轻微擦边 = normal
4. 只有【真正恶意、严重攻击性】才标记敏感
5. should_reply=true 只在发现真正恶意内容时
6. 宁可放过，不要误判！
7. reason字段如果是normal就留空""
8. 仅返回JSON，不要markdown，不要其他内容"""

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
            except json.JSONDecodeError as je:
                logger.error(f"批量敏感词JSON解析失败: {type(je).__name__} - {je}")
                logger.error(f"LLM完整返回: {content}")
                # 尝试修复JSON
                try:
                    # 如果JSON被截断，尝试补全
                    if not content.endswith('}'):
                        # 计算缺少的闭合括号
                        open_braces = content.count('{')
                        close_braces = content.count('}')
                        open_brackets = content.count('[')
                        close_brackets = content.count(']')
                        
                        # 补全缺失的括号
                        content += ']' * (open_brackets - close_brackets)
                        content += '}' * (open_braces - close_braces)
                    
                    result = json.loads(content)
                    logger.info("JSON修复成功，继续处理")
                except:
                    logger.error("JSON修复失败，跳过此次批量检测")
                    return
            
            # 处理检测结果，扣减功德并通知
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
                        today_merit, total_merit = db.deduct_merit(group_id, user_id, nickname, 1)
                        logger.info(f"LLM检测扣功德: {nickname}({user_id}) 类型={sensitive_type}, 当前功德={total_merit}")
                        
                        # 立即通知用户
                        notify_msg = Message([MessageSegment.at(user_id)])
                        notify_msg.append(MessageSegment.text(f" 功德 -1 (当前: {total_merit})"))
                        await bot.send_group_msg(group_id=int(group_id), message=notify_msg)
                    except Exception as e:
                        logger.error(f"扣减功德失败: {e}")
            
            # 发送回复（更多变、更俏皮）
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
                
                # 根据类型选择图片和俏皮回复
                if sensitive_type == "sexist":
                    img_bytes = get_special_image("有股味(有猪味).jpg")
                    reply_content = random.choice([
                        "有股味了喵~",
                        "这话...有点那个喵",
                        "呜 小喵闻到奇怪的味道",
                        "emmm 这个...喵？",
                        "哎呀 又来了喵",
                    ])
                elif sensitive_type == "nsfw":
                    img_bytes = get_special_image("猪出警.jpg")
                    reply_content = random.choice([
                        "不可以涩涩喵！",
                        "猪猪出警啦！",
                        "呜...好害羞喵",
                        "这个不行的啦！",
                        "小喵要报警了喵！",
                        "色色是不对的喵~",
                    ])
                elif sensitive_type == "muslim":
                    img_name = random.choice(["猪吃回民.jpg", "猪降临(清真).jpg"])
                    img_bytes = get_special_image(img_name)
                    reply_content = random.choice([
                        "猪来咯~",
                        "清真警告喵！",
                        "猪猪降临啦",
                        "呜 这个话题...",
                        "小喵觉得不太好喵",
                    ])
                elif sensitive_type == "politics":
                    reply_content = random.choice([
                        "呜...这个小喵不敢说喵",
                        "这个话题太危险了喵",
                        "小喵不懂政治喵~",
                        "咱还是聊点别的吧喵",
                    ])
                elif sensitive_type == "rude":
                    img_bytes = get_special_image("猪币.jpg")
                    reply_content = random.choice([
                        "小喵不理你了！",
                        "哼！好凶喵...",
                        "呜呜 被骂了",
                        "说话这么凶干嘛喵",
                        "温柔一点嘛~",
                        "不要这样啦喵",
                    ])
                
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

        # === AI 判断是否需要联网搜索 ===
        search_results = None
        if config.search_enabled:
            search_query = await should_search_and_get_query(text_content)
            if search_query:
                logger.info(f"AI判断需要搜索，关键词: {search_query}")
                search_results = await search_web(search_query, max_results=3)
                if search_results:
                    logger.info(f"搜索成功，结果长度: {len(search_results)}")
                else:
                    logger.warning("搜索失败或无结果")

        # === LLM敏感词检测 ===
        sensitive_result = await check_single_message_sensitive(text_content)
        if sensitive_result and sensitive_result.get("type") != "normal":
            sensitive_type = sensitive_result.get("type", "")
            reason = sensitive_result.get("reason", "")
            logger.info(f"@机器人检测到敏感内容: {sensitive_type} - {reason}")
            
            # 扣减功德
            try:
                db = get_unified_db()
                today_merit, total_merit = db.deduct_merit(group_id, user_id, nickname, 1)
                logger.info(f"扣功德: {nickname}({user_id}) 类型={sensitive_type}, 当前功德={total_merit}")
            except Exception as e:
                logger.error(f"扣减功德失败: {e}")
                total_merit = "?"
            
            # 构建回复（更俏皮多变）
            msg = Message()
            msg.append(MessageSegment.at(user_id))
            msg.append(MessageSegment.text(" "))
            
            img_bytes = None
            reply_text = ""
            
            if sensitive_type == "sexist":
                img_bytes = get_special_image("有股味(有猪味).jpg")
                reply_text = random.choice([
                    "有股味了喵~",
                    "这话...有点那个喵",
                    "呜 小喵闻到奇怪的味道",
                    "emmm 这个...喵？",
                    "哎呀 又来了喵",
                ])
            elif sensitive_type == "nsfw":
                img_bytes = get_special_image("猪出警.jpg")
                reply_text = random.choice([
                    "不可以涩涩喵！",
                    "猪猪出警啦！",
                    "呜...好害羞喵",
                    "这个不行的啦！",
                    "小喵要报警了喵！",
                    "色色是不对的喵~",
                ])
            elif sensitive_type == "muslim":
                img_name = random.choice(["猪吃回民.jpg", "猪降临(清真).jpg"])
                img_bytes = get_special_image(img_name)
                reply_text = random.choice([
                    "猪来咯~",
                    "清真警告喵！",
                    "猪猪降临啦",
                    "呜 这个话题...",
                    "小喵觉得不太好喵",
                ])
            elif sensitive_type == "politics":
                reply_text = random.choice([
                    "呜...这个小喵不敢说喵",
                    "这个话题太危险了喵",
                    "小喵不懂政治喵~",
                    "咱还是聊点别的吧喵",
                ])
            elif sensitive_type == "rude":
                img_bytes = get_special_image("猪币.jpg")
                reply_text = random.choice([
                    "小喵不理你了！",
                    "哼！好凶喵...",
                    "呜呜 被骂了",
                    "说话这么凶干嘛喵",
                    "温柔一点嘛~",
                    "不要这样啦喵",
                ])
            
            if img_bytes:
                msg.append(MessageSegment.image(img_bytes))
            msg.append(MessageSegment.text(f"{reply_text}\n功德 -1 (当前: {total_merit})"))
            
            await ai_chat.finish(msg)
            return

        # 保存用户消息到数据库
        db = get_unified_db()
        db.add_conversation(group_id, user_id, "user", text_content)

        # 获取持久化的对话历史（减少到3条，降低历史存在感）
        conversation = db.get_conversation(group_id, user_id, limit=3)

        # 获取当前用户的完整数据
        user_data = db.get_or_create_user(group_id, user_id, nickname)
        
        # 构建当前用户的数据摘要（简洁版）
        caller_data = {
            "nickname": nickname,
            "today_merit": user_data.today_merit,
            "total_merit": user_data.total_merit,
            "today_length": user_data.today_length,
            "fish_count": user_data.fish_count,
            "collection_count": db.get_collection_count(group_id, user_id),
            "current_title": user_data.current_title,
            "profile": user_data.profile,
            "tags": user_data.tags,
        }
        
        # 检测用户是否在询问其他人的信息
        # 简单的启发式：检测是否包含昵称+问号
        mentioned_user_data = None
        mentioned_nickname = None
        
        # 尝试从消息中提取可能的昵称（简单匹配）
        # 例如："ss喜欢吃什么？" -> 提取"ss"
        import re
        # 匹配中文、英文、数字组成的昵称（2-10个字符）
        potential_nicknames = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,10}', text_content)
        
        for potential_nick in potential_nicknames:
            if potential_nick != nickname:  # 不是自己
                # 尝试从数据库查询这个昵称
                all_users = db.get_all_users_in_group(group_id)
                for u in all_users:
                    if u.nickname and potential_nick in u.nickname:
                        mentioned_user_data = u
                        mentioned_nickname = u.nickname
                        break
                if mentioned_user_data:
                    break
        
        current_date = datetime.now().strftime("%Y年%m月%d日 %A")

        # 极简猫娘人设 - 优先回答问题
        system_content = f"""你是小喵，一只可爱的猫娘。今天是{current_date}。

【核心原则】
- 优先回答用户的问题，给出有用的信息
- 说话简短自然，偶尔用"喵"、"呢"、"啦"
- 不要过度沉浸角色扮演

【对话者信息】
昵称: {nickname}
功德: {caller_data['total_merit']} | 长度: {caller_data['today_length']}cm | 钓鱼: {caller_data['fish_count']}次
{f"头衔: {caller_data['current_title']}" if caller_data['current_title'] else ""}"""

        # 如果有搜索结果，添加到 system prompt
        if search_results:
            system_content += f"""

【联网搜索结果】
{search_results}

（用户的问题可能需要最新信息，请参考上面的搜索结果回答）"""

        # 如果检测到询问其他人，添加被询问者的信息
        if mentioned_user_data:
            mentioned_collection = db.get_collection_count(group_id, mentioned_user_data.user_id)
            system_content += f"""

【被询问的人】
昵称: {mentioned_nickname}
功德: {mentioned_user_data.total_merit} | 长度: {mentioned_user_data.today_length}cm | 钓鱼: {mentioned_user_data.fish_count}次
{f"头衔: {mentioned_user_data.current_title}" if mentioned_user_data.current_title else ""}
{f"特点: {mentioned_user_data.profile}" if mentioned_user_data.profile else ""}

（用户在询问{mentioned_nickname}的信息，请根据上面的数据回答）"""

        system_content += """

【回答规则】
- 用户问功德/长度/钓鱼等数据时，直接用上面的数据回答
- 用户问其他人的信息时，用"被询问的人"的数据回答
- 用户问其他问题时，正常回答，不要说"小喵不知道"
- 不懂的问题可以说"这个小喵不太懂呢"
- 政治话题说"呜...这个小喵不敢说喵"
"""

        system_prompt = {"role": "system", "content": system_content}

        messages = [system_prompt] + conversation

        ai_response = await call_ai_api(messages, max_tokens=None, temperature=0.85)

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

        # === 词云统计 ===
        try:
            add_message_to_wordcloud(group_id, text_content)
        except Exception as e:
            logger.error(f"词云统计异常: {e}")

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


# ========== 群精华消息自动处理 ==========

essence_notice = on_notice(priority=10, block=False)

@essence_notice.handle()
async def handle_essence_notice(bot: Bot, event: Event):
    """监听精华消息事件，自动分析人设"""
    try:
        # 检查是否是精华消息通知
        if not isinstance(event, NoticeEvent):
            return
        
        # OneBot V11 精华消息事件：notice_type=notify, sub_type=essence
        if event.notice_type != "notify":
            return
        
        # 获取 sub_type（可能在不同字段）
        sub_type = getattr(event, "sub_type", None)
        if sub_type != "essence":
            return
        
        # 获取群号和消息ID
        group_id = str(getattr(event, "group_id", ""))
        message_id = getattr(event, "message_id", None)
        sender_id = str(getattr(event, "sender_id", ""))
        
        if not group_id or not message_id:
            return
        
        logger.info(f"检测到精华消息事件: 群{group_id}, 消息ID={message_id}, 发送者={sender_id}")
        
        # 获取消息详情
        try:
            msg_info = await bot.call_api("get_msg", message_id=message_id)
        except Exception as e:
            logger.error(f"获取精华消息详情失败: {e}")
            return
        
        # 提取消息内容
        user_id = str(msg_info.get("sender", {}).get("user_id", sender_id))
        nickname = msg_info.get("sender", {}).get("card") or msg_info.get("sender", {}).get("nickname", "")
        
        # 提取文本内容
        message_data = msg_info.get("message", "")
        text_content = ""
        
        if isinstance(message_data, str):
            text_content = message_data
        elif isinstance(message_data, list):
            for seg in message_data:
                if isinstance(seg, dict) and seg.get("type") == "text":
                    text_content += seg.get("data", {}).get("text", "")
        
        text_content = text_content.strip()
        
        if not text_content or not user_id:
            logger.warning(f"精华消息内容为空或无用户ID")
            return
        
        # 添加消息到数据库
        db = get_unified_db()
        db.add_message(group_id, user_id, text_content)
        
        # 获取当前缓冲消息数量
        msg_count = len(db.get_buffer_messages(group_id, user_id))
        
        # 如果达到触发条件，立即分析
        if profile_analyzer.should_analyze(msg_count):
            logger.info(f"精华消息触发人设分析: {nickname}({user_id})")
            await profile_analyzer.analyze_and_update(group_id, user_id)
        else:
            logger.info(f"精华消息已添加到缓冲: {nickname}({user_id}), 当前缓冲数={msg_count}")
        
    except Exception as e:
        logger.error(f"精华消息事件处理异常: {e}")


# ========== 群精华消息手动处理 ==========
