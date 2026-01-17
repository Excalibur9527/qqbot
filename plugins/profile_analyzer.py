"""
群友人设分析模块
调用 LLM 分析消息并生成/更新用户人设、标签、重要事件
"""

import re
import json
from typing import Dict, List, Optional, Union
import httpx
from nonebot.log import logger

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config


class ProfileAnalyzer:
    """群友人设分析器"""
    
    def __init__(self, db):
        """
        初始化分析器
        db: UnifiedDatabase 或 ProfileDatabase 实例
        """
        self.db = db
        self.trigger_count = 5  # 从10条改为5条
    
    def build_analysis_prompt(self, messages: List[Dict], old_profile: Optional[str], 
                               old_tags: List[str], old_memories: List[Dict]) -> str:
        """构建 LLM 分析 prompt"""
        msg_lines = [f"{i}. {msg['content']}" for i, msg in enumerate(messages, 1)]
        messages_text = "\n".join(msg_lines)
        
        profile_section = old_profile if old_profile else "暂无"
        tags_section = ", ".join(old_tags) if old_tags else "暂无"
        memories_section = "\n".join([f"- {m['event']}" for m in old_memories]) if old_memories else "暂无"
        
        prompt = f"""你是用户画像分析师。根据群聊记录分析用户特征。

【现有人设】
{profile_section}

【现有标签】
{tags_section}

【历史重要事件】
{memories_section}

【新增聊天记录】
{messages_text}

【分析要求】
1. 更新人设描述（50字以内，简洁自然）
2. 更新标签（3-5个关键词，如：游戏党、程序员、二次元、话痨、夜猫子）
3. 提取重要事件（如：考研上岸、换工作、分手、生日等，没有就留空）

【重要提示】
- 说的话不一定代表该用户本人，要精准判断
- 例如："ss喜欢吃什么？" -> 这是在问别人，不代表该用户喜欢吃什么
- 只记录确定的、关于该用户自己的信息
- 不确定的信息不要记录

【输出JSON格式】
{{
    "profile": "人设描述",
    "tags": ["标签1", "标签2", "标签3"],
    "new_event": "重要事件（没有则为空字符串）"
}}
仅返回JSON，不要markdown"""

        return prompt
    
    def parse_llm_response(self, response: str) -> Dict:
        """解析 LLM 返回"""
        try:
            # 清理 markdown
            response = response.replace("```json", "").replace("```", "").strip()
            result = json.loads(response)
            return {
                "profile": result.get("profile", ""),
                "tags": result.get("tags", []),
                "new_event": result.get("new_event", "")
            }
        except:
            # 解析失败，返回原文作为人设
            return {"profile": response.strip(), "tags": [], "new_event": ""}
    
    async def call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM API"""
        if not config.ai_api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{config.ai_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.ai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": config.ai_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    logger.error(f"LLM API 调用失败: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"LLM API 调用异常: {e}")
            return None
    
    async def analyze_and_update(self, group_id: str, user_id: str) -> Optional[str]:
        """分析用户消息并更新人设、标签、事件"""
        messages = self.db.get_buffer_messages(group_id, user_id)
        if not messages:
            return None
        
        message_count = len(messages)
        
        # 获取现有数据 - 兼容 UnifiedDatabase
        user_data = self.db.get_user(group_id, user_id)
        if user_data:
            old_profile = user_data.profile if hasattr(user_data, 'profile') else None
            old_tags = user_data.tags if hasattr(user_data, 'tags') else []
            old_nickname = user_data.nickname if hasattr(user_data, 'nickname') else None
        else:
            old_profile = None
            old_tags = []
            old_nickname = None
        
        old_memories = self.db.get_memories(group_id, user_id)
        
        # 构建 prompt 并调用 LLM
        prompt = self.build_analysis_prompt(messages, old_profile, old_tags, old_memories)
        logger.info(f"开始分析用户 {user_id} 人设，消息数: {message_count}")
        
        llm_response = await self.call_llm(prompt)
        if not llm_response:
            logger.error("LLM 分析失败")
            return None
        
        # 解析结果
        result = self.parse_llm_response(llm_response)
        profile = result["profile"]
        tags = result["tags"]
        new_event = result["new_event"]
        
        # 更新数据库 - 使用 UnifiedDatabase 的方法
        self.db.update_profile(group_id, user_id, profile, tags)
        
        # 如果有新的重要事件，记录下来
        if new_event and len(new_event) > 2:
            self.db.add_memory(group_id, user_id, new_event)
            logger.info(f"用户 {user_id} 新增记忆: {new_event}")
        
        # 清空缓冲
        self.db.clear_buffer(group_id, user_id)
        
        logger.info(f"用户 {user_id} 人设已更新，标签: {tags}")
        return profile
    
    def should_analyze(self, message_count: int) -> bool:
        return message_count >= self.trigger_count
