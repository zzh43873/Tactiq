"""
Agent基类定义
参考MiroFish设计，每个实体都是独立Agent
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class Action(BaseModel):
    """行动定义"""
    type: str  # diplomatic, military, economic, propaganda
    target: Optional[str]
    content: str
    intensity: float  # 0-1
    expected_outcome: str


class Perception(BaseModel):
    """感知结果"""
    event_understanding: str
    threat_assessment: float  # -1 to 1
    opportunity_assessment: float  # -1 to 1
    affected_interests: List[str]


class Decision(BaseModel):
    """决策结果"""
    selected_action: Action
    rationale: str
    alternative_considered: List[str]
    confidence: float


class Message(BaseModel):
    """Agent间通信消息"""
    sender: str
    receiver: str
    type: str  # THREAT, PROMISE, REQUEST, INFO
    content: str
    intensity: float
    timestamp: datetime


class AgentMemory:
    """
    Agent记忆系统
    存储历史互动、承诺、信誉等信息
    """
    
    def __init__(self, capacity: int = 100):
        self.short_term: List[Dict] = []  # 当前推演中的事件
        self.long_term: Dict[str, Any] = {}   # 历史知识和关系模式
        self.commitments: List[Dict] = []  # 已做出的承诺
        self.trust_scores: Dict[str, float] = {}  # 对其他Agent的信任评分
        self.capacity = capacity
    
    def add(self, event: Dict):
        """添加记忆"""
        self.short_term.append({
            **event,
            "timestamp": datetime.now()
        })
        # 限制容量
        if len(self.short_term) > self.capacity:
            self.short_term.pop(0)
    
    def recall_similar(self, event: Dict, k: int = 3) -> List[Dict]:
        """回忆相似历史事件"""
        # TODO: 实现相似度匹配
        return self.short_term[-k:] if len(self.short_term) >= k else self.short_term
    
    def get_commitments(self) -> List[Dict]:
        """获取已做出的承诺"""
        return [e for e in self.short_term 
                if e.get("type") == "commitment"]
    
    def update_trust(self, agent_id: str, delta: float):
        """更新对其他Agent的信任度"""
        current = self.trust_scores.get(agent_id, 0.5)
        self.trust_scores[agent_id] = max(0, min(1, current + delta))
    
    def get_trust(self, agent_id: str) -> float:
        """获取对其他Agent的信任度"""
        return self.trust_scores.get(agent_id, 0.5)


class EntityAgent(ABC):
    """
    地缘政治实体Agent基类
    参考MiroFish设计，每个实体都是独立Agent
    """
    
    def __init__(self, entity_id: str, entity_profile: Dict):
        self.entity_id = entity_id
        self.profile = entity_profile
        self.memory = AgentMemory()
        self.state = {
            "current_emotion": "neutral",
            "trust_levels": {},  # 对其他实体的信任度
            "commitments": [],   # 已做出的承诺
            "resources": entity_profile.get("attributes", {})
        }
    
    @abstractmethod
    def perceive(self, event: Dict, context: Dict) -> Perception:
        """
        感知阶段：理解事件对自身的意义
        每个实体Agent根据自己的画像和记忆来理解事件
        """
        pass
    
    @abstractmethod
    def decide(self, perception: Perception, 
               available_actions: List[Action],
               other_agents_states: Dict) -> Decision:
        """
        决策阶段：选择应对策略
        考虑自身利益、能力、约束条件
        """
        pass
    
    @abstractmethod
    def act(self, decision: Decision) -> Action:
        """
        行动阶段：执行决策
        """
        pass
    
    def communicate(self, target_agent: str, message_type: str, 
                   content: str, intensity: float = 0.5) -> Message:
        """
        通信阶段：与其他Agent交互
        """
        return Message(
            sender=self.entity_id,
            receiver=target_agent,
            type=message_type,
            content=content,
            intensity=intensity,
            timestamp=datetime.now()
        )
    
    def update_memory(self, event: Dict):
        """更新记忆"""
        self.memory.add(event)
    
    def update_trust(self, agent_id: str, delta: float):
        """更新对其他Agent的信任度"""
        self.state["trust_levels"][agent_id] = self.memory.get_trust(agent_id) + delta
        self.memory.update_trust(agent_id, delta)
    
    def get_profile_summary(self) -> str:
        """获取实体画像摘要"""
        return f"""
实体: {self.profile.get('name', self.entity_id)}
类型: {self.profile.get('type', 'unknown')}
核心利益: {', '.join(self.profile.get('core_interests', []))}
关键属性: {self.profile.get('attributes', {})}
"""
