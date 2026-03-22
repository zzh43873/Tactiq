"""
LLM Provider 抽象接口
定义统一的LLM调用规范
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """LLM消息"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    
    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role=MessageRole.SYSTEM, content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role=MessageRole.USER, content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "Message":
        return cls(role=MessageRole.ASSISTANT, content=content)
    
    def to_dict(self) -> Dict[str, Any]:
        # 兼容 role 是字符串或 MessageRole 枚举的情况
        role_value = self.role.value if isinstance(self.role, MessageRole) else self.role
        result = {"role": role_value, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


@dataclass
class Usage:
    """Token使用情况"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class Response:
    """LLM响应"""
    content: str
    role: MessageRole = MessageRole.ASSISTANT
    tool_calls: Optional[List[Dict]] = None
    usage: Optional[Usage] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None  # 原始响应，用于调试
    
    def get_tool_calls(self) -> List[Dict]:
        """获取工具调用"""
        return self.tool_calls or []
    
    def has_tool_calls(self) -> bool:
        """是否有工具调用"""
        return bool(self.tool_calls and len(self.tool_calls) > 0)


class LLMProvider(ABC):
    """
    LLM Provider 抽象基类
    
    所有LLM提供商都需要实现此接口
    """
    
    def __init__(self, model: str, temperature: float = 0.3, **kwargs):
        self.model = model
        self.temperature = temperature
        self.config = kwargs
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Response:
        """
        对话接口
        
        Args:
            messages: 消息列表
            tools: 可用工具列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            LLM响应
        """
        pass
    
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式对话接口
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            响应文本片段
        """
        pass
    
    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """
        文本嵌入接口
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """获取模型名称"""
        pass
    
    def _prepare_messages(self, messages: List[Message]) -> List[Dict]:
        """将消息转换为提供商格式"""
        return [m.to_dict() for m in messages]
    
    def _prepare_tools(self, tools: Optional[List[Tool]]) -> Optional[List[Dict]]:
        """将工具转换为提供商格式"""
        if not tools:
            return None
        return [t.to_dict() for t in tools]
