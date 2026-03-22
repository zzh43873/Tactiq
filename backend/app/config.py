"""
应用配置管理
使用Pydantic Settings管理环境变量和配置
"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Determine the correct .env file path
# When running in Docker, env vars are passed directly
# When running locally, look for .env in parent directory
_env_file_path = ".env"
if os.path.exists("../.env"):
    _env_file_path = "../.env"


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=_env_file_path,
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # === 应用基础配置 ===
    APP_NAME: str = Field(default="Tactiq System")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    
    # === 数据库配置 ===
    # 默认使用 SQLite，避免 asyncpg 编译问题
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./tactiq.db")
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_USER: str = Field(default="user")
    DB_PASSWORD: str = Field(default="password")
    DB_NAME: str = Field(default="geopolitics")
    
    # === Redis配置 ===
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    
    # === LLM API配置 ===
    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview")
    
    # Anthropic (Claude)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_MODEL: str = Field(default="claude-3-opus-20240229")
    
    # DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None)
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat")
    
    # 硅基流动
    SILICONFLOW_API_KEY: Optional[str] = Field(default=None)
    SILICONFLOW_BASE_URL: str = Field(default="https://api.siliconflow.cn/v1")
    SILICONFLOW_MODEL: str = Field(default="Qwen/Qwen2.5-72B-Instruct")
    
    # === 外部数据源配置 ===
    # GDELT
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = Field(default=None)
    
    # NewsAPI
    NEWSAPI_KEY: Optional[str] = Field(default=None)
    
    # ACLED
    ACLED_API_KEY: Optional[str] = Field(default=None)
    ACLED_EMAIL: Optional[str] = Field(default=None)
    
    # === Celery配置 ===
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0")
    
    # === 推演配置 ===
    SIMULATION_MAX_ROUNDS: int = Field(default=5)
    SIMULATION_TIMEOUT: int = Field(default=300)  # 秒
    
    @property
    def database_url(self) -> str:
        """获取数据库URL"""
        return self.DATABASE_URL
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.APP_ENV == "development"
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.APP_ENV == "production"


# 全局配置实例
settings = Settings()
