"""
SiliconFlow Provider 实现
"""
from typing import List, Optional, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from loguru import logger

from .provider import LLMProvider, Message, Response, Tool, Usage


class SiliconFlowProvider(LLMProvider):
    """SiliconFlow API 提供商 (OpenAI兼容格式)"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "Qwen/Qwen2.5-72B-Instruct",
        base_url: str = "https://api.siliconflow.cn/v1",
        temperature: float = 0.3,
        **kwargs
    ):
        super().__init__(model=model, temperature=temperature, **kwargs)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Response:
        """对话接口实现"""
        try:
            params = {
                "model": self.model,
                "messages": self._prepare_messages(messages),
                "temperature": temperature or self.temperature,
            }
            
            if tools:
                params["tools"] = self._prepare_tools(tools)
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            params.update(kwargs)
            
            result = await self.client.chat.completions.create(**params)
            
            choice = result.choices[0]
            message = choice.message
            
            usage = None
            if result.usage:
                usage = Usage(
                    prompt_tokens=result.usage.prompt_tokens,
                    completion_tokens=result.usage.completion_tokens,
                    total_tokens=result.usage.total_tokens
                )
            
            return Response(
                content=message.content or "",
                tool_calls=message.tool_calls if hasattr(message, 'tool_calls') else None,
                usage=usage,
                model=result.model,
                finish_reason=choice.finish_reason,
                raw_response=result
            )
            
        except Exception as e:
            logger.error(f"SiliconFlow API error: {e}")
            raise
    
    async def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话接口实现"""
        try:
            params = {
                "model": self.model,
                "messages": self._prepare_messages(messages),
                "temperature": temperature or self.temperature,
                "stream": True,
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            params.update(kwargs)
            
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"SiliconFlow streaming error: {e}")
            raise
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """文本嵌入接口实现"""
        try:
            model = kwargs.get("model", "BAAI/bge-large-zh-v1.5")
            
            result = await self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            return [item.embedding for item in result.data]
            
        except Exception as e:
            logger.error(f"SiliconFlow embedding error: {e}")
            raise
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return f"siliconflow/{self.model}"
