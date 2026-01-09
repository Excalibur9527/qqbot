import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """配置文件类"""

    # --- OneBot 连接配置 ---
    # 默认值设为本地回环，具体配置写在 .env 中
    onebot_ws_urls: List[str] = ["ws://127.0.0.1:3001"]
    onebot_access_token: Optional[str] = None  # 敏感信息设为 None

    # --- 机器人配置 ---
    bot_qq: str = "12345678"  # 默认占位符
    superusers: List[str] = []
    
    # --- NoneBot 配置 ---
    command_start: set = {"", "/"}
    command_sep: set = {".", " "}

    # --- AI 大模型配置 ---
    # 敏感信息不写在代码里，由系统环境变量或 .env 自动注入
    ai_api_key: Optional[str] = None
    ai_base_url: str = "https://api.example.com/v1"
    ai_model: str = "gpt-3.5-turbo"
    ai_max_tokens: int = 1000
    ai_temperature: float = 0.7

    # --- 插件配置 ---
    length_plugin_enabled: bool = True
    ai_chat_plugin_enabled: bool = True
    ai_auto_reply_enabled: bool = True
    ai_context_buffer_size: int = 5
    test_plugin_enabled: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
config = Config()