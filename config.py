"""
配置文件
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """配置文件类"""

    # OneBot 连接配置
    # 注意：这里配置的是NapCat WebSocket服务器的地址
    # 如果NapCat在远程服务器上，需要改为对应的IP地址和端口
    onebot_ws_urls: List[str] = ["ws://lama:3001"]  # Docker环境使用服务名
    onebot_access_token: str = "A,Fb*=CMI2L7WQp&"  # 如果NapCat设置了token，在这里配置

    # 机器人配置
    bot_qq: str = "3161152960"  # 替换为你的机器人QQ号
    superusers: List[str] = []
    
    # NoneBot 配置
    command_start: set = {"", "/"}  # 允许空前缀（直接说话）和斜杠前缀
    command_sep: set = {".", " "}   # 命令分隔符

    # AI 大模型配置
    ai_api_key: Optional[str] = "sk-RPK9DoC7E3wJubMZbygCY4Ut0OiSyMdosgdsnFXj8kAdYHFU"
    ai_base_url: str = "https://api.34ku.com/v1"
    ai_model: str = "gemini-3-flash-preview-nothinking"
    ai_max_tokens: int = 1000
    ai_temperature: float = 0.7
    
    # 联网搜索配置（SearXNG）
    search_enabled: bool = True  # 是否启用联网搜索
    # Docker host网络模式用 localhost，bridge网络模式用容器名
    search_url: str = os.getenv("SEARXNG_URL", "http://localhost:8080")  # SearXNG 搜索服务地址

    # 插件配置
    length_plugin_enabled: bool = True
    ai_chat_plugin_enabled: bool = True
    ai_auto_reply_enabled: bool = True  # 是否开启AI自动插话
    ai_context_buffer_size: int = 5     # 自动插话的上下文缓冲大小
    test_plugin_enabled: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
config = Config()
