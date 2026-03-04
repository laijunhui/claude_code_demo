# 配置管理
import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # MiniMax API 配置
    minimax_api_key: str = "sk-api-8XSp0cpjg5b3WY4tnrJBncu8zASNZOlLMkpJAgjcI0olSyvR7qVi5CFygnkMrnAWudYVX0IpIxjwB1FImfeRn4XOjzYTQQbKO6WzjQSpk9GsHjQQ0BLCKGE"
    minimax_model: str = "MiniMax-M2.1"
    minimax_base_url: str = "https://api.minimaxi.com/v1"

    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000

    # 安全配置
    api_token: str = "dev-token-change-in-production"

    # GitHub 配置
    github_token: str = ""
    github_webhook_secret: str = ""

    # 评审配置
    max_file_size: int = 1024 * 1024  # 1MB
    max_files_per_review: int = 50

    # 日志配置
    log_level: str = "INFO"
    log_dir: str = "logs"

    # 存储配置
    storage_base_dir: str = "data/reviews"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
