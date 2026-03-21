"""
实体Agent模块
"""

from .hamas import HamasAgent
from .usa import USAAgent

__all__ = ["HamasAgent", "USAAgent"]

# 实体Agent注册表
ENTITY_AGENTS = {
    "hamas": HamasAgent,
    "usa": USAAgent,
    # TODO: 添加更多实体Agent
    # "china": ChinaAgent,
    # "russia": RussiaAgent,
    # "israel": IsraelAgent,
    # "iran": IranAgent,
    # "hezbollah": HezbollahAgent,
}


def get_agent_class(entity_id: str):
    """获取Agent类"""
    return ENTITY_AGENTS.get(entity_id)


def create_agent(entity_id: str):
    """创建Agent实例"""
    agent_class = get_agent_class(entity_id)
    if agent_class:
        return agent_class()
    return None
