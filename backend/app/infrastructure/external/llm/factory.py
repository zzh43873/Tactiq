"""
LLM Provider 工厂
根据配置自动选择合适的提供商
"""
from typing import Optional
from loguru import logger

from app.config import settings
from .provider import LLMProvider
from .openai_provider import OpenAIProvider
from .deepseek_provider import DeepSeekProvider
from .siliconflow_provider import SiliconFlowProvider


class LLMFactory:
    """
    LLM Provider 工厂
    
    根据环境变量配置自动创建合适的LLM Provider
    优先级: OpenAI > DeepSeek > SiliconFlow
    """
    
    @classmethod
    def create(
        cls,
        prefer_fast: bool = True,
        temperature: float = 0.3
    ) -> LLMProvider:
        """
        创建LLM Provider
        
        Args:
            prefer_fast: 是否优先使用快速模型
            temperature: 温度参数
            
        Returns:
            LLMProvider实例
            
        Raises:
            ValueError: 当没有配置任何API Key时
        """
        # 优先级1: OpenAI
        if settings.OPENAI_API_KEY:
            logger.info(f"Creating OpenAI provider with model {settings.OPENAI_MODEL}")
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                base_url=settings.OPENAI_BASE_URL,
                temperature=temperature
            )
        
        # 优先级2: DeepSeek
        if settings.DEEPSEEK_API_KEY:
            logger.info(f"Creating DeepSeek provider with model {settings.DEEPSEEK_MODEL}")
            return DeepSeekProvider(
                api_key=settings.DEEPSEEK_API_KEY,
                model=settings.DEEPSEEK_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=temperature
            )
        
        # 优先级3: SiliconFlow
        if settings.SILICONFLOW_API_KEY:
            logger.info(f"Creating SiliconFlow provider with model {settings.SILICONFLOW_MODEL}")
            return SiliconFlowProvider(
                api_key=settings.SILICONFLOW_API_KEY,
                model=settings.SILICONFLOW_MODEL,
                base_url=settings.SILICONFLOW_BASE_URL,
                temperature=temperature
            )
        
        raise ValueError(
            "No LLM API key configured. "
            "Please set one of: OPENAI_API_KEY, DEEPSEEK_API_KEY, or SILICONFLOW_API_KEY"
        )
    
    @classmethod
    def create_with_fallback(
        cls,
        prefer_fast: bool = True,
        temperature: float = 0.3
    ) -> Optional[LLMProvider]:
        """
        创建LLM Provider（带降级处理）
        
        如果没有配置任何API Key，返回None而不是抛出异常
        """
        try:
            return cls.create(prefer_fast, temperature)
        except ValueError:
            logger.warning("No LLM provider available")
            return None
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """获取可用的提供商列表"""
        available = []
        if settings.OPENAI_API_KEY:
            available.append("openai")
        if settings.DEEPSEEK_API_KEY:
            available.append("deepseek")
        if settings.SILICONFLOW_API_KEY:
            available.append("siliconflow")
        return available
