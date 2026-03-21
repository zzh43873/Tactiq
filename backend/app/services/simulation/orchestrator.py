"""
推演控制器（Orchestrator）
协调整个推演流程：情报收集 → Agent构建 → 多轮推演 → 红队挑战 → 综合评估
"""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from app.services.intelligence.collector import IntelligenceCollector, IntelligenceReport
from app.services.simulation.agents.factory import AgentFactory
from app.services.simulation.agents.base import EntityAgent, Action, Perception, Decision
from app.schemas.simulation import (
    SimulationConfig,
    SimulationResult,
    RoundResult,
    AgentAction,
    Interaction,
    SimulationPath,
    TimelineNode,
    RedTeamChallenge,
    Synthesis
)


class SimulationOrchestrator:
    """
    推演控制器
    协调整个地缘政治推演流程
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.intelligence_collector = IntelligenceCollector()
        self.agent_factory = AgentFactory()
        
        # 推演状态
        self.agents: List[EntityAgent] = []
        self.current_round = 0
        self.round_results: List[RoundResult] = []
        self.interactions: List[Interaction] = []
    
    async def run_simulation(self, event_description: str) -> SimulationResult:
        """
        运行完整推演流程

        Args:
            event_description: 事件描述（用户输入的命题）

        Returns:
            完整的推演结果
        """
        logger.info(f"Starting simulation: {event_description[:100]}...")

        try:
            # Step 1: 情报收集
            logger.info("Step 1: Collecting intelligence...")
            intelligence = await self.intelligence_collector.collect(event_description)
            logger.info(f"Identified {len(intelligence.identified_entities)} entities from content analysis")
            
            # 如果内容分析没有识别到实体，但预识别阶段有实体，使用预识别实体
            if len(intelligence.identified_entities) == 0:
                pre_identified = self.intelligence_collector.pre_identified_entities
                if pre_identified:
                    logger.info(f"No entities from content analysis, using {len(pre_identified)} pre-identified entities")
                    # 将预识别实体转换为EntityIdentification格式
                    # 支持字典格式（来自缓存）和对象格式（来自LLM预识别）
                    from app.services.intelligence.collector import EntityIdentification
                    converted_entities = []
                    for e in pre_identified:
                        if isinstance(e, dict):
                            # 字典格式（来自缓存）
                            converted_entities.append(EntityIdentification(
                                name=e.get('name', ''),
                                name_en=e.get('name_en'),
                                entity_type=e.get('entity_type', 'unknown'),
                                role=e.get('role', 'unknown'),
                                relevance_score=e.get('relevance', 0.5),
                                current_actions=e.get('current_actions', []),
                                stated_position=e.get('stated_position', ''),
                                key_interests=e.get('key_interests', [])
                            ))
                        else:
                            # 对象格式（来自LLM预识别）
                            converted_entities.append(EntityIdentification(
                                name=getattr(e, 'name', ''),
                                name_en=getattr(e, 'name_en', None),
                                entity_type=getattr(e, 'entity_type', 'unknown'),
                                role=getattr(e, 'role', 'unknown'),
                                relevance_score=getattr(e, 'relevance', 0.5),
                                current_actions=getattr(e, 'current_actions', []),
                                stated_position=getattr(e, 'stated_position', ''),
                                key_interests=getattr(e, 'key_interests', [])
                            ))
                    intelligence.identified_entities = converted_entities
                    logger.info(f"Populated {len(intelligence.identified_entities)} entities from pre-identification")

            # Step 2: 动态构建Agent
            logger.info("Step 2: Creating agents dynamically...")
            self.agents = self.agent_factory.create_agents(intelligence)
            logger.info(f"Created {len(self.agents)} agents")

            # Step 3: 初始化推演环境
            logger.info("Step 3: Initializing simulation environment...")
            simulation_state = self._initialize_simulation(intelligence)

            # Step 4: 多轮推演
            logger.info("Step 4: Running multi-round simulation...")
            max_rounds = self.config.max_rounds or 5
            
            # 清空之前的回合结果
            self.round_results = []

            for round_num in range(1, max_rounds + 1):
                logger.info(f"Running round {round_num}/{max_rounds} with {len(self.agents)} agents...")
                round_result = await self._run_round(round_num, simulation_state)
                self.round_results.append(round_result)
                logger.info(f"Round {round_num} completed with {len(round_result.actions)} actions")

                # 检查是否达到稳定状态或提前结束条件
                if self._should_stop_early(round_result):
                    logger.info("Early termination condition met")
                    break

            # Step 5: 生成推演路径
            logger.info("Step 5: Extracting simulation paths...")
            paths = self._extract_paths()
            logger.info(f"Extracted {len(paths)} simulation paths with {sum(len(p.nodes) for p in paths)} total nodes")

            # Step 6: 红队挑战
            logger.info("Step 6: Red team challenge...")
            red_team_challenges = await self._red_team_challenge(paths)

            # Step 7: 综合评估
            logger.info("Step 7: Synthesis and evaluation...")
            synthesis = await self._synthesize(paths, red_team_challenges)

            # 构建最终结果
            from uuid import uuid4
            result = SimulationResult(
                simulation_id=str(uuid4()),
                event_id=str(uuid4()),  # TODO: 从数据库获取
                participating_agents=[agent.entity_id for agent in self.agents],
                rounds=self.round_results,
                paths=paths,
                red_team_challenges=red_team_challenges,
                synthesis=synthesis
            )

            logger.info("Simulation completed successfully")
            return result

        except Exception as e:
            logger.error(f"Simulation failed: {e}", exc_info=True)
            raise
    
    def _initialize_simulation(self, intelligence: IntelligenceReport) -> Dict:
        """初始化推演环境"""
        state = {
            "intelligence": intelligence,
            "current_situation": {
                "military_deployments": intelligence.military_deployments,
                "diplomatic_activities": intelligence.diplomatic_activities,
                "economic_measures": intelligence.economic_measures
            },
            "agent_states": {},
            "global_context": {
                "timeframe": intelligence.timeframe,
                "background": intelligence.background
            }
        }
        
        # 初始化每个Agent的状态
        for agent in self.agents:
            state["agent_states"][agent.entity_id] = {
                "trust_levels": {},
                "commitments": [],
                "last_action": None
            }
        
        return state
    
    async def _run_round(self, round_num: int, simulation_state: Dict) -> RoundResult:
        """
        运行单轮推演
        
        每轮包括：
        1. 感知阶段：各Agent理解当前态势
       2. 决策阶段：各Agent选择行动
        3. 行动阶段：执行行动并记录
        4. 交互阶段：Agent间通信和协商
        """
        actions = []
        interactions = []
        
        logger.info(f"Round {round_num}: Processing {len(self.agents)} agents")
        
        # Phase 1 & 2 & 3: 感知-决策-行动
        for agent in self.agents:
            try:
                # 感知
                perception = self._agent_perceive(agent, simulation_state)
                
                # 决策
                decision = self._agent_decide(agent, perception, simulation_state)
                
                # 行动
                action = self._agent_act(agent, decision)
                
                # 记录行动
                agent_action = AgentAction(
                    agent_id=agent.entity_id,
                    agent_name=agent.profile.get("name", agent.entity_id),
                   action=action,
                    rationale=decision.rationale,
                   confidence=decision.confidence
                )
                actions.append(agent_action)
                logger.debug(f"Agent {agent.entity_id} action: {action.content}")
                
                # 更新Agent状态
                self._update_agent_state(agent, action, simulation_state)
                
            except Exception as e:
                logger.error(f"Agent {agent.entity_id} failed in round {round_num}: {e}", exc_info=True)
                continue
        
        logger.info(f"Round {round_num}: {len(actions)} agents successfully acted")
        
        # Phase 4: 交互（简化版，TODO: 实现复杂交互逻辑）
        interactions = self._generate_interactions(actions, simulation_state)
        
        # 更新全局态势
        self._update_global_state(actions, interactions, simulation_state)
        
        # 生成回合总结
        summary = self._generate_round_summary(round_num, actions, interactions)

        return RoundResult(
            round_number=round_num,
            actions=actions,
            interactions=interactions,
            summary=summary
        )
    
    def _agent_perceive(self, agent: EntityAgent, state: Dict) -> Perception:
        """Agent感知阶段"""
        event = {
            "type": "simulation_event",
            "actor": "system",
            "description": f"Round {self.current_round + 1}, current situation..."
        }
        context = state["global_context"]
        return agent.perceive(event, context)
    
    def _agent_decide(
        self, 
       agent: EntityAgent,
        perception: Perception,
        state: Dict
    ) -> Decision:
        """Agent决策阶段"""
        available_actions = self._generate_available_actions(agent, state)
        other_states = state["agent_states"]
        return agent.decide(perception, available_actions, other_states)
    
    def _agent_act(self, agent: EntityAgent, decision: Decision) -> Action:
        """Agent行动阶段"""
        return agent.act(decision)
    
    def _generate_available_actions(self, agent: EntityAgent, state: Dict) -> List[Action]:
        """生成可用行动列表"""
        # TODO: 根据情境生成合理的行动选项
        return [
            Action(
                type="diplomatic",
                target=None,
                content="发表声明",
                intensity=0.3,
                expected_outcome="表达立场"
            ),
            Action(
                type="economic",
               target=None,
               content="经济措施",
                intensity=0.5,
                expected_outcome="施加压力"
            ),
            Action(
                type="military",
               target=None,
               content="军事部署",
                intensity=0.4,
                expected_outcome="威慑对手"
            )
        ]
    
    def _update_agent_state(
        self, 
        agent: EntityAgent,
        action: Action,
        state: Dict
    ):
        """更新Agent状态"""
        agent_state = state["agent_states"].get(agent.entity_id, {})
        agent_state["last_action"] = action
        state["agent_states"][agent.entity_id] = agent_state
    
    def _generate_interactions(
        self, 
        actions: List[AgentAction],
        state: Dict
    ) -> List[Interaction]:
        """生成Agent间交互"""
        interactions = []
        
        # 简化版：检测盟友间的协调
        for action in actions:
            if action.action.type == "diplomatic":
                # 查找盟友
                allies = self._find_allies(action.agent_id)
                if allies:
                    interactions.append(Interaction(
                        type="bilateral",
                        participants=[action.agent_id, allies[0]],
                      content=f"{action.agent_name}向盟友通报立场",
                       outcome="协调立场"
                    ))
        
        return interactions
    
    def _find_allies(self, agent_id: str) -> List[str]:
        """查找盟友"""
        # TODO: 从关系网络中查找
        return []
    
    def _update_global_state(
        self, 
        actions: List[AgentAction],
        interactions: List[Interaction],
        state: Dict
    ):
        """更新全局态势"""
        # TODO: 根据行动和交互更新态势
        pass
    
    def _generate_round_summary(
        self, 
        round_num: int,
        actions: List[AgentAction],
        interactions: List[Interaction]
    ) -> str:
        """生成回合总结"""
        summary_lines = [f"Round {round_num} summary:"]
        
        for action in actions[:5]:  # 只显示前5个行动
            summary_lines.append(f"- {action.agent_name}: {action.action.content}")
        
        return "\n".join(summary_lines)
    
    def _should_stop_early(self, round_result: RoundResult) -> bool:
        """检查是否应提前结束"""
        # TODO: 实现提前结束逻辑（如达成稳定状态）
        return False
    
    def _extract_paths(self) -> List[SimulationPath]:
        """从推演结果中提取因果路径，用于可视化展示"""
        from app.schemas.simulation import CausalNode, CausalEdge
        
        paths = []
        all_round_nodes = []  # 存储所有回合的节点，用于跨回合连接
        
        logger.info(f"Extracting paths from {len(self.round_results)} round results")
        
        # 详细调试日志
        for i, rr in enumerate(self.round_results):
            logger.info(f"Round {i+1}: {len(rr.actions)} actions, {len(rr.interactions)} interactions")
            for j, action in enumerate(rr.actions):
                logger.info(f"  Action {j+1}: {action.agent_name} - {action.action.content if action.action else 'NO ACTION'}")
        
        # 检查是否有回合结果
        if not self.round_results:
            logger.warning("No round results available, creating default paths")
            return self._create_default_paths()
        
        # 为每个推演回合生成因果节点
        for round_idx, round_result in enumerate(self.round_results):
            logger.info(f"Processing round {round_idx + 1}: {len(round_result.actions)} actions, {len(round_result.interactions)} interactions")
            nodes = []
            edges = []
            
            # 将每个Agent的行动转换为因果节点
            for action_idx, agent_action in enumerate(round_result.actions):
                node_id = f"r{round_idx}_a{action_idx}"
                
                # 检查 action 字段是否存在
                if not agent_action.action:
                    logger.warning(f"Action {action_idx} has no action data: {agent_action}")
                    continue
                
                action = agent_action.action
                logger.debug(f"Creating node for action: {action.content if hasattr(action, 'content') else str(action)}")
                
                # 确定维度
                dimension = self._classify_action_dimension(action)
                
                # 确定时间尺度
                timeframe = self._classify_timeframe(round_idx, len(self.round_results))
                
                # 获取地理位置
                location = self._get_entity_location(agent_action.agent_id)
                
                try:
                    node = CausalNode(
                        id=node_id,
                        entity=agent_action.agent_name,
                        entity_type=self._get_entity_type(agent_action.agent_id),
                        action=action.content if hasattr(action, 'content') else str(action),
                        dimension=dimension,
                        timeframe=timeframe,
                        description=agent_action.rationale,
                        impact=agent_action.confidence,
                        location=location,
                        round_number=round_idx + 1
                    )
                    nodes.append(node)
                    logger.info(f"Created node {node_id}: {agent_action.agent_name} - {action.content if hasattr(action, 'content') else str(action)}")
                except Exception as e:
                    logger.error(f"Failed to create CausalNode for action {action_idx}: {e}")
                    continue
                
                # 创建与前一轮节点的因果关系
                if round_idx > 0 and all_round_nodes:
                    # 从所有历史节点中获取前一轮的节点
                    prev_round_nodes = [n for n in all_round_nodes if n.round_number == round_idx]
                    if prev_round_nodes:
                        # 连接前一轮的高影响力节点到当前节点
                        sorted_prev = sorted(prev_round_nodes, key=lambda x: x.impact or 0, reverse=True)
                        for prev_node in sorted_prev[:3]:  # 连接前一轮的前3个高影响力节点
                            edge = CausalEdge(
                                source=prev_node.id,
                                target=node_id,
                                label="引发",
                                type="causal",
                                strength=min(0.9, 0.5 + (prev_node.impact or 0) * 0.4)
                            )
                            edges.append(edge)
            
            # 添加交互产生的节点
            for inter_idx, interaction in enumerate(round_result.interactions):
                node_id = f"r{round_idx}_i{inter_idx}"
                
                node = CausalNode(
                    id=node_id,
                    entity="系统",
                    entity_type="interaction",
                    action=interaction.content,
                    dimension="diplomatic",
                    timeframe=self._classify_timeframe(round_idx, len(self.round_results)),
                    description=interaction.outcome,
                    impact=0.6,
                    location=None,
                    round_number=round_idx + 1
                )
                nodes.append(node)
            
            # 保存当前回合的节点到全局列表
            all_round_nodes.extend(nodes)
            
            # 创建路径
            if nodes:
                logger.info(f"Creating path for round {round_idx + 1} with {len(nodes)} nodes, {len(edges)} edges")
                # 转换 CausalNode 为 TimelineNode 用于 timeline 字段
                timeline_nodes = [
                    TimelineNode(
                        id=n.id,
                        event=n.action,
                        actor=n.entity,
                        action=n.dimension,
                        timeframe=n.timeframe,
                        description=n.description
                    )
                    for n in nodes
                ]
                
                path = SimulationPath(
                    id=f"path_{round_idx + 1}",
                    name=f"推演路径 {round_idx + 1}",
                    assumption=f"基于第{round_idx + 1}轮推演结果",
                    probability=0.5,
                    confidence="medium",
                    nodes=nodes,
                    edges=edges,
                    timeline={
                        "short": [n for n in timeline_nodes if n.timeframe == "short"],
                        "medium": [n for n in timeline_nodes if n.timeframe == "medium"],
                        "long": [n for n in timeline_nodes if n.timeframe == "long"]
                    }
                )
                paths.append(path)
        
        # 如果没有生成路径，创建默认路径
        if not paths:
            logger.warning(f"No paths generated from {len(self.round_results)} rounds, creating default paths")
            paths = self._create_default_paths()
        else:
            total_nodes = sum(len(p.nodes) for p in paths)
            logger.info(f"Successfully generated {len(paths)} paths with {total_nodes} total nodes")
        
        return paths
    
    def _classify_action_dimension(self, action) -> str:
        """分类行动维度"""
        content = action.content.lower() if hasattr(action, 'content') else str(action).lower()
        action_type = action.type.lower() if hasattr(action, 'type') else ""
        
        if any(kw in content or kw in action_type for kw in ['军事', '军队', '打击', '攻击', '部署', '演习', 'military', 'attack', 'deploy']):
            return "military"
        elif any(kw in content or kw in action_type for kw in ['经济', '制裁', '贸易', '投资', 'economic', 'sanction', 'trade']):
            return "economic"
        elif any(kw in content or kw in action_type for kw in ['外交', '谈判', '对话', '声明', 'diplomatic', 'negotiate', 'talk']):
            return "diplomatic"
        else:
            return "public_opinion"
    
    def _classify_timeframe(self, round_idx: int, total_rounds: int) -> str:
        """根据回合数分类时间尺度"""
        if total_rounds <= 1:
            return "short"
        ratio = round_idx / (total_rounds - 1)
        if ratio < 0.33:
            return "short"
        elif ratio < 0.66:
            return "medium"
        else:
            return "long"
    
    def _get_entity_location(self, agent_id: str) -> Optional[Dict]:
        """获取实体地理位置"""
        location_map = {
            "usa": {"lat": 39.8283, "lng": -98.5795, "name": "美国"},
            "china": {"lat": 35.8617, "lng": 104.1954, "name": "中国"},
            "russia": {"lat": 61.5240, "lng": 105.3188, "name": "俄罗斯"},
            "iran": {"lat": 32.4279, "lng": 53.6880, "name": "伊朗"},
            "israel": {"lat": 31.0461, "lng": 34.8516, "name": "以色列"},
            "saudi": {"lat": 23.8859, "lng": 45.0792, "name": "沙特阿拉伯"},
            "hamas": {"lat": 31.5, "lng": 34.47, "name": "加沙地带"},
            "hezbollah": {"lat": 33.8547, "lng": 35.8623, "name": "黎巴嫩"},
            "houthis": {"lat": 15.5527, "lng": 48.5164, "name": "也门"},
        }
        
        agent_id_lower = agent_id.lower()
        for key, location in location_map.items():
            if key in agent_id_lower:
                return location
        return None
    
    def _get_entity_type(self, agent_id: str) -> str:
        """获取实体类型"""
        country_keywords = ['usa', 'china', 'russia', 'iran', 'israel', 'saudi']
        org_keywords = ['eu', 'nato', 'un']
        
        agent_id_lower = agent_id.lower()
        if any(kw in agent_id_lower for kw in country_keywords):
            return "country"
        elif any(kw in agent_id_lower for kw in org_keywords):
            return "organization"
        else:
            return "non_state_actor"
    
    def _create_default_paths(self) -> List[SimulationPath]:
        """创建默认路径（当推演没有产生结果时）"""
        from app.schemas.simulation import CausalNode, CausalEdge, TimelineNode
        
        default_causal_node = CausalNode(
            id="n1",
            entity="系统",
            entity_type="system",
            action="推演进行中",
            dimension="diplomatic",
            timeframe="short",
            description="推演尚未产生完整结果",
            impact=0.5,
            location=None,
            round_number=1
        )
        
        default_timeline_node = TimelineNode(
            id="n1",
            event="推演进行中",
            actor="系统",
            action="diplomatic",
            timeframe="short",
            description="推演尚未产生完整结果"
        )
        
        return [
            SimulationPath(
                id="default_path",
                name="推演路径",
                assumption="基于当前情报",
                probability=0.5,
                confidence="low",
                nodes=[default_causal_node],
                edges=[],
                timeline={"short": [default_timeline_node], "medium": [], "long": []}
            )
        ]
    
    async def _red_team_challenge(self, paths: List[SimulationPath]) -> List[RedTeamChallenge]:
        """红队挑战"""
        from app.services.simulation.red_team import RedTeamChallenger
        
        challenger = RedTeamChallenger(llm_client=self.intelligence_collector.llm_client)
        
        participating_agents = [agent.entity_id for agent in self.agents]
        event_description = self.config.event_description if hasattr(self.config, 'event_description') else "推演事件"
        
        challenges = await challenger.challenge_paths(
            paths=paths,
            event_description=event_description,
            participating_agents=participating_agents
        )
        
        return challenges
    
    async def _synthesize(
        self, 
       paths: List[SimulationPath],
        challenges: List[RedTeamChallenge]
    ) -> Synthesis:
        """综合评估"""
        # TODO: 实现综合评估逻辑
        return Synthesis(
            key_uncertainties=[],
            early_warning_indicators=[],
            overall_assessment="推演完成",
            strategic_implications=[]
        )
