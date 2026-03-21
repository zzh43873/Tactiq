"""
红队挑战系统
实现对抗性验证，通过AI挑战推演假设，发现盲点
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger
import json

from app.schemas.simulation import SimulationPath, RedTeamChallenge, CausalNode
from app.config import settings


@dataclass
class ChallengePoint:
    """挑战点"""
    target_path_id: str
    assumption: str  # 被挑战的假设
    challenge_type: str  # 挑战类型
    severity: str  # 严重程度 (high/medium/low)
    rationale: str  # 挑战理由


class RedTeamChallenger:
    """
    红队挑战者
    通过多维度分析推演路径，识别假设漏洞和盲点
    """
    
    CHALLENGE_TYPES = [
        "rationality",      # 理性假设挑战
        "information",      # 信息完整性挑战
        "cascade",          # 连锁反应挑战
        "external",         # 外部因素挑战
        "temporal",         # 时间尺度挑战
        "capability",       # 能力评估挑战
    ]
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
    async def challenge_paths(
        self,
        paths: List[SimulationPath],
        event_description: str,
        participating_agents: List[str]
    ) -> List[RedTeamChallenge]:
        """
        对推演路径进行红队挑战
        
        Args:
            paths: 推演路径列表
            event_description: 事件描述
            participating_agents: 参与Agent列表
            
        Returns:
            红队挑战列表
        """
        logger.info(f"Starting red team challenge for {len(paths)} paths")
        
        challenges = []
        
        # 1. 基于规则的启发式挑战（快速）
        heuristic_challenges = self._generate_heuristic_challenges(
            paths, event_description, participating_agents
        )
        challenges.extend(heuristic_challenges)
        
        # 2. 基于LLM的深度挑战（如果配置了LLM）
        if self.llm_client and len(paths) > 0:
            llm_challenges = await self._generate_llm_challenges(
                paths, event_description, participating_agents
            )
            challenges.extend(llm_challenges)
        
        # 3. 去重和排序
        challenges = self._deduplicate_challenges(challenges)
        challenges = sorted(challenges, key=lambda x: self._severity_score(x), reverse=True)
        
        logger.info(f"Generated {len(challenges)} red team challenges")
        return challenges[:5]  # 返回前5个最重要的挑战
    
    def _generate_heuristic_challenges(
        self,
        paths: List[SimulationPath],
        event_description: str,
        agents: List[str]
    ) -> List[RedTeamChallenge]:
        """基于启发式规则生成挑战"""
        challenges = []
        
        for path in paths:
            # 挑战1: 理性决策假设
            challenges.append(RedTeamChallenge(
                target_path=path.id,
                challenge=f"路径'{path.name}'假设所有参与方都理性决策，但现实中可能受国内政治、情绪、误判等因素影响",
                alternative_scenario="考虑非理性因素：某方因国内政治压力采取冒险行动，或领导人个人决策风格导致意外升级",
                key_assumption_questioned="理性行为体假设"
            ))
            
            # 挑战2: 信息对称假设
            if len(agents) > 2:
                challenges.append(RedTeamChallenge(
                    target_path=path.id,
                    challenge=f"推演假设各方信息相对对称，但现实中信息可能高度不对称",
                    alternative_scenario="某方掌握关键情报但选择隐瞒，或错误情报导致误判",
                    key_assumption_questioned="信息对称假设"
                ))
            
            # 挑战3: 单一路径依赖
            if len(paths) == 1:
                challenges.append(RedTeamChallenge(
                    target_path=path.id,
                    challenge="只生成了一条推演路径，可能忽略了重要的分支可能性",
                    alternative_scenario="考虑多方同时行动、第三方介入、意外事件触发等复杂场景",
                    key_assumption_questioned="路径完整性"
                ))
            
            # 挑战4: 时间压力
            challenges.append(RedTeamChallenge(
                target_path=path.id,
                challenge="推演假设各方有充足时间评估和决策，但危机中时间压力可能导致仓促决策",
                alternative_scenario="时间压力下，某方在信息不全时做出冲动决策，导致局势失控",
                key_assumption_questioned="决策时间假设"
            ))
            
            # 挑战5: 外部因素
            challenges.append(RedTeamChallenge(
                target_path=path.id,
                challenge="推演主要考虑直接参与方，可能忽略了第三方、媒体、公众舆论等外部因素",
                alternative_scenario="社交媒体放大事件、国际舆论压力、意外事件（如恐怖袭击）改变局势",
                key_assumption_questioned="封闭系统假设"
            ))
        
        return challenges
    
    async def _generate_llm_challenges(
        self,
        paths: List[SimulationPath],
        event_description: str,
        agents: List[str]
    ) -> List[RedTeamChallenge]:
        """使用LLM生成深度挑战"""
        challenges = []
        
        try:
            # 准备路径摘要
            path_summaries = []
            for path in paths[:3]:  # 只分析前3条路径
                nodes_summary = " -> ".join([
                    f"{n.entity}: {n.action}" 
                    for n in path.nodes[:5]
                ])
                path_summaries.append(f"路径 {path.name}: {nodes_summary}")
            
            path_summaries_text = '\n'.join(path_summaries)
            agents_text = ', '.join(agents)
            
            prompt = f"""作为红队分析师，请对以下地缘政治推演进行批判性挑战。

事件背景：{event_description}

参与方：{agents_text}

推演路径：
{path_summaries_text}

请从以下角度提出3个关键挑战：
1. 推演中隐含的关键假设是什么？这些假设有多可靠？
2. 哪些因素被低估了或完全忽略了？
3. 什么情况下推演路径会完全偏离？

输出格式（JSON）：
{{
  "challenges": [
    {{
      "type": "挑战类型",
      "target": "针对哪个路径或假设",
      "challenge": "具体挑战内容",
      "alternative": "替代情景",
      "severity": "high/medium/low"
    }}
  ]
}}
"""
            
            response = await self.llm_client.chat.completions.create(
                model=settings.OPENAI_MODEL or "gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "你是地缘政治分析专家，擅长识别推演中的假设盲点和逻辑漏洞。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content
            
            # 解析JSON
            import re
            try:
                # 尝试提取JSON
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    
                    for ch in result.get("challenges", []):
                        challenges.append(RedTeamChallenge(
                            target_path=ch.get("target", "all"),
                            challenge=ch.get("challenge", ""),
                            alternative_scenario=ch.get("alternative", ""),
                            key_assumption_questioned=ch.get("type", "未知假设")
                        ))
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM red team response as JSON")
                
        except Exception as e:
            logger.error(f"LLM red team challenge failed: {e}")
        
        return challenges
    
    def _deduplicate_challenges(self, challenges: List[RedTeamChallenge]) -> List[RedTeamChallenge]:
        """去重挑战"""
        seen = set()
        unique = []
        
        for ch in challenges:
            # 基于关键假设去重
            key = ch.key_assumption_questioned
            if key not in seen:
                seen.add(key)
                unique.append(ch)
        
        return unique
    
    def _severity_score(self, challenge: RedTeamChallenge) -> int:
        """计算挑战严重程度分数"""
        score = 0
        
        # 基础分数
        severity_keywords = {
            "high": 10,
            "medium": 5,
            "low": 2
        }
        
        # 根据假设重要性加分
        critical_assumptions = ["理性", "信息", "时间", "路径完整性"]
        for assumption in critical_assumptions:
            if assumption in challenge.key_assumption_questioned:
                score += 5
        
        # 根据挑战内容长度（信息丰富度）
        score += min(len(challenge.challenge) // 50, 5)
        
        return score


class AdversarialSimulator:
    """
    对抗性模拟器
    模拟不同立场AI之间的对抗辩论
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def run_debate(
        self,
        proposition: str,
        paths: List[SimulationPath],
        rounds: int = 3
    ) -> Dict[str, Any]:
        """
        运行对抗辩论
        
        Args:
            proposition: 辩论命题
            paths: 推演路径
            rounds: 辩论轮数
            
        Returns:
            辩论结果
        """
        logger.info(f"Starting adversarial debate for: {proposition}")
        
        debate_log = []
        
        for round_num in range(1, rounds + 1):
            # 正方（支持推演结果）
            pro_response = await self._generate_debate_response(
                proposition, paths, "pro", round_num, debate_log
            )
            debate_log.append({"round": round_num, "side": "pro", "content": pro_response})
            
            # 反方（挑战推演结果）
            con_response = await self._generate_debate_response(
                proposition, paths, "con", round_num, debate_log
            )
            debate_log.append({"round": round_num, "side": "con", "content": con_response})
        
        # 总结
        summary = await self._summarize_debate(debate_log)
        
        return {
            "debate_log": debate_log,
            "summary": summary,
            "key_insights": self._extract_insights(debate_log)
        }
    
    async def _generate_debate_response(
        self,
        proposition: str,
        paths: List[SimulationPath],
        side: str,
        round_num: int,
        history: List[Dict]
    ) -> str:
        """生成辩论回应"""
        if not self.llm_client:
            return f"{side.upper()} side response (round {round_num})"
        
        side_prompt = {
            "pro": "你是推演结果的支持者。请论证推演路径的合理性和可能性。",
            "con": "你是推演结果的挑战者。请指出推演中的漏洞、盲点和替代可能性。"
        }
        
        history_text = "\n\n".join([
            f"Round {h['round']} ({h['side']}): {h['content'][:200]}..."
            for h in history[-4:]  # 最近4条
        ])
        
        prompt = f"""{side_prompt[side]}

命题：{proposition}

辩论历史：
{history_text}

请给出你的第{round_num}轮回应（200字以内）：
"""
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=settings.OPENAI_MODEL or "gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": side_prompt[side]},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Debate response generation failed: {e}")
            return f"Error generating {side} response"
    
    async def _summarize_debate(self, debate_log: List[Dict]) -> str:
        """总结辩论"""
        # 简化实现
        pro_points = [d["content"] for d in debate_log if d["side"] == "pro"]
        con_points = [d["content"] for d in debate_log if d["side"] == "con"]
        
        return f"辩论总结：正方提出{len(pro_points)}个论点，反方提出{len(con_points)}个挑战。建议综合考虑双方观点。"
    
    def _extract_insights(self, debate_log: List[Dict]) -> List[str]:
        """提取关键洞察"""
        insights = []
        
        # 简单的关键词提取
        for entry in debate_log:
            content = entry["content"].lower()
            if "假设" in content or "assumption" in content:
                insights.append("推演依赖的关键假设需要验证")
            if "盲点" in content or "blind" in content:
                insights.append("存在未被考虑的因素")
            if "风险" in content or "risk" in content:
                insights.append("推演可能低估了风险")
        
        return list(set(insights))[:3]  # 去重，最多3条
