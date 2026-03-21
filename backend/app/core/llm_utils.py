"""
LLM调用工具类
提供带超时、重试、错误处理的LLM调用封装
"""

import asyncio
from typing import Optional, Callable, Any, TypeVar, Generic
from functools import wraps
from datetime import datetime
from loguru import logger
import json

T = TypeVar('T')


class LLMTimeoutError(Exception):
    """LLM调用超时错误"""
    pass


class LLMRetryError(Exception):
    """LLM调用重试耗尽错误"""
    pass


class LLMCallManager:
    """
    LLM调用管理器
    提供超时控制、重试机制、错误处理
    """
    
    DEFAULT_TIMEOUT = 60  # 默认超时60秒
    DEFAULT_RETRIES = 3   # 默认重试3次
    DEFAULT_BACKOFF = 2   # 默认退避系数
    
    @classmethod
    async def call_with_timeout(
        cls,
        func: Callable[..., Any],
        timeout: Optional[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        带超时的异步调用
        
        Args:
            func: 要执行的异步函数
            timeout: 超时时间（秒）
            *args, **kwargs: 函数参数
            
        Returns:
            函数执行结果
            
        Raises:
            LLMTimeoutError: 调用超时
        """
        timeout = timeout or cls.DEFAULT_TIMEOUT
        
        try:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"LLM call timed out after {timeout}s")
            raise LLMTimeoutError(f"LLM调用超时（{timeout}秒）")
    
    @classmethod
    async def call_with_retry(
        cls,
        func: Callable[..., Any],
        max_retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF,
        timeout: Optional[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        带重试的异步调用
        
        Args:
            func: 要执行的异步函数
            max_retries: 最大重试次数
            backoff_factor: 退避系数
            timeout: 每次调用的超时时间
            *args, **kwargs: 函数参数
            
        Returns:
            函数执行结果
            
        Raises:
            LLMRetryError: 重试耗尽
            LLMTimeoutError: 调用超时
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = backoff_factor ** (attempt - 1)
                    logger.info(f"Retrying LLM call (attempt {attempt}/{max_retries}) after {wait_time}s...")
                    await asyncio.sleep(wait_time)
                
                return await cls.call_with_timeout(func, timeout, *args, **kwargs)
                
            except LLMTimeoutError:
                # 超时错误不重试，直接抛出
                raise
            except Exception as e:
                last_exception = e
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                
                # 如果是最后尝试，抛出重试错误
                if attempt == max_retries:
                    raise LLMRetryError(f"LLM调用重试{max_retries}次后仍然失败: {last_exception}")
        
        # 不应该到达这里
        raise LLMRetryError("Unexpected error in retry logic")
    
    @classmethod
    def safe_json_parse(cls, text: str, default: Any = None) -> Any:
        """
        安全解析JSON
        
        Args:
            text: JSON文本
            default: 解析失败时的默认值
            
        Returns:
            解析后的对象或默认值
        """
        if not text:
            return default
            
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            import re
            
            # 匹配JSON对象
            patterns = [
                r'\{[\s\S]*?\}',  # 匹配花括号内的内容
                r'```json\s*([\s\S]*?)\s*```',  # 匹配markdown代码块
                r'```\s*([\s\S]*?)\s*```',  # 匹配无语言标记的代码块
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue
            
            logger.warning(f"Failed to parse JSON from text: {text[:200]}...")
            return default


class LLMClientWrapper:
    """
    LLM客户端包装器
    为OpenAI/Anthropic等客户端提供统一的超时控制接口
    """
    
    def __init__(self, client: Any, provider: str = "openai"):
        """
        初始化包装器
        
        Args:
            client: LLM客户端实例
            provider: 提供商名称 (openai/anthropic/deepseek)
        """
        self.client = client
        self.provider = provider
        self.timeout = LLMCallManager.DEFAULT_TIMEOUT
    
    async def chat_completion(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        带超时的聊天完成调用
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间
            **kwargs: 其他参数
            
        Returns:
            API响应
        """
        timeout = timeout or self.timeout
        
        async def _call():
            if self.provider == "openai":
                return await self.client.chat.completions.create(
                    model=model or "gpt-4-turbo-preview",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            elif self.provider == "anthropic":
                return await self.client.messages.create(
                    model=model or "claude-3-opus-20240229",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or 4096,
                    **kwargs
                )
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        
        return await LLMCallManager.call_with_timeout(_call, timeout)
    
    async def chat_completion_with_retry(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Any:
        """
        带重试的聊天完成调用
        """
        async def _call():
            return await self.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs
            )
        
        return await LLMCallManager.call_with_retry(
            _call,
            max_retries=max_retries,
            timeout=timeout
        )


def llm_call(
    timeout: Optional[float] = None,
    max_retries: int = 3,
    backoff_factor: float = 2.0
):
    """
    LLM调用装饰器
    
    用法:
        @llm_call(timeout=30, max_retries=2)
        async def my_llm_function():
            return await openai_client.chat.completions.create(...)
    
    Args:
        timeout: 超时时间
        max_retries: 最大重试次数
        backoff_factor: 退避系数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中提取timeout参数（如果调用时指定）
            call_timeout = kwargs.pop('call_timeout', timeout)
            
            async def _wrapped():
                return await func(*args, **kwargs)
            
            return await LLMCallManager.call_with_retry(
                _wrapped,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
                timeout=call_timeout
            )
        return wrapper
    return decorator
