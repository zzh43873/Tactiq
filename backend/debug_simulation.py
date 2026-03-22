"""
推演引擎单独调试脚本

使用方式:
    cd backend
    python debug_simulation.py

功能:
    1. 不启动完整服务，直接测试推演引擎
    2. 支持单步调试
    3. 可自定义命题和实体
    4. 输出详细的中间结果
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional

# 设置环境变量
os.environ["APP_ENV"] = "development"
os.environ["DEBUG"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./debug.db"

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/debug_simulation.log",
    rotation="10 MB",
    level="DEBUG"
)


async def test_decision_engine():
    """测试决策引擎（鹰鸽辩论）"""
    logger.info("=" * 60)
    logger.info("测试决策引擎 - 鹰鸽辩论")
    logger.info("=" * 60)
    
    from app.domain.entities import GeopoliticalEntity, EntityType, EntityRole
    from app.domain.services import DecisionEngine, DebateContext
    from app.infrastructure.external.llm import LLMFactory
    
    # 创建 LLM Provider
    llm = LLMFactory.create(temperature=0.7)
    
    # 创建决策引擎
    engine = DecisionEngine(llm)
    
    # 创建测试实体
    entity = GeopoliticalEntity(
        name="美国",
        name_en="United States",
        entity_type=EntityType.SOVEREIGN_STATE,
        role=EntityRole.INITIATOR,
        relevance_score=1.0,
        core_interests=["国家安全", "中东影响力", "核不扩散"]
    )
    
    # 创建辩论上下文
    context = DebateContext(
        proposition="特朗普宣布出动地面部队攻击伊朗",
        round_number=1,
        previous_decisions=[],
        other_entities=[],  # 简化测试
        situation_summary="紧张局势升级，伊朗核设施成为焦点"
    )
    
    logger.info(f"实体: {entity.name}")
    logger.info(f"命题: {context.proposition}")
    logger.info(f"核心利益: {entity.core_interests}")
    logger.info("-" * 60)
    
    # 执行决策
    try:
        decision = await engine.make_decision(entity, context)
        
        logger.info("决策结果:")
        logger.info(f"  行动类型: {decision.action_type.value}")
        logger.info(f"  行动内容: {decision.action_content}")
        logger.info(f"  决策理由: {decision.reasoning}")
        logger.info(f"  信心程度: {decision.confidence}")
        logger.info(f"  国内成本: {decision.domestic_cost}")
        logger.info(f"  国际风险: {decision.international_risk}")
        logger.info(f"  预期结果: {decision.expected_outcome}")
        
        return decision
        
    except Exception as e:
        logger.error(f"决策失败: {e}")
        raise


async def test_simulation_engine():
    """测试完整推演引擎"""
    logger.info("\n" + "=" * 60)
    logger.info("测试推演引擎 - LangGraph 四阶段流水线")
    logger.info("=" * 60)
    
    from app.domain.services import SimulationEngine
    from app.infrastructure.external.llm import LLMFactory
    
    # 创建 LLM Provider
    llm = LLMFactory.create(temperature=0.5)
    
    # 创建推演引擎
    engine = SimulationEngine(llm)
    
    # 测试命题
    proposition = "特朗普宣布出动地面部队攻击伊朗"
    simulation_id = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"推演ID: {simulation_id}")
    logger.info(f"命题: {proposition}")
    logger.info(f"最大轮数: 2 (调试用)")
    logger.info("-" * 60)
    
    try:
        # 执行推演
        result = await engine.run_simulation(
            simulation_id=simulation_id,
            proposition=proposition,
            entities=None,  # 让引擎自动识别实体
            max_rounds=2    # 调试用，只跑2轮
        )
        
        # 输出结果
        logger.info("\n推演完成!")
        logger.info(f"状态: {result.status.value}")
        logger.info(f"识别实体数: {len(result.entities)}")
        logger.info(f"推演轮数: {len(result.rounds)}")
        
        # 输出识别的实体
        logger.info("\n识别的实体:")
        for entity in result.entities:
            logger.info(f"  - {entity.name} ({entity.entity_type.value})")
        
        # 输出每轮结果
        logger.info("\n推演过程:")
        for round_result in result.rounds:
            logger.info(f"\n  第 {round_result.round_number} 轮:")
            logger.info(f"  局势: {round_result.situation_summary}")
            logger.info(f"  决策数: {len(round_result.decisions)}")
            
            for decision in round_result.decisions:
                logger.info(f"    [{decision.entity_name}] {decision.action_type.value}: {decision.action_content[:50]}...")
        
        # 输出最终报告
        if result.final_report:
            logger.info("\n最终报告:")
            logger.info(result.final_report[:500] + "...")
        
        # 保存结果到文件
        output_file = f"debug_result_{simulation_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "simulation_id": result.simulation_id,
                "proposition": result.proposition,
                "status": result.status.value,
                "entities": [
                    {
                        "name": e.name,
                        "type": e.entity_type.value,
                        "interests": e.core_interests
                    }
                    for e in result.entities
                ],
                "rounds": [
                    {
                        "round": r.round_number,
                        "summary": r.situation_summary,
                        "decisions": [
                            {
                                "entity": d.entity_name,
                                "action": d.action_content,
                                "type": d.action_type.value,
                                "confidence": d.confidence,
                                "risk": d.international_risk
                            }
                            for d in r.decisions
                        ]
                    }
                    for r in result.rounds
                ],
                "final_report": result.final_report
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n结果已保存到: {output_file}")
        
        return result
        
    except Exception as e:
        logger.error(f"推演失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


async def test_with_custom_entities():
    """使用自定义实体测试推演"""
    logger.info("\n" + "=" * 60)
    logger.info("测试推演引擎 - 使用自定义实体")
    logger.info("=" * 60)
    
    from app.domain.entities import GeopoliticalEntity, EntityType, EntityRole
    from app.domain.services import SimulationEngine
    from app.infrastructure.external.llm import LLMFactory
    
    # 创建 LLM Provider
    llm = LLMFactory.create(temperature=0.5)
    
    # 创建推演引擎
    engine = SimulationEngine(llm)
    
    # 自定义实体
    entities = [
        GeopoliticalEntity(
            name="美国",
            entity_type=EntityType.SOVEREIGN_STATE,
            role=EntityRole.INITIATOR,
            core_interests=["国家安全", "全球霸权", "核不扩散"]
        ),
        GeopoliticalEntity(
            name="伊朗",
            entity_type=EntityType.SOVEREIGN_STATE,
            role=EntityRole.TARGET,
            core_interests=["国家主权", "核技术发展", "地区影响力"]
        ),
        GeopoliticalEntity(
            name="以色列",
            entity_type=EntityType.SOVEREIGN_STATE,
            role=EntityRole.STAKEHOLDER,
            core_interests=["国家安全", "防止伊朗拥核"]
        )
    ]
    
    proposition = "伊朗宣布成功试射洲际弹道导弹"
    simulation_id = f"debug_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"推演ID: {simulation_id}")
    logger.info(f"命题: {proposition}")
    logger.info(f"预定义实体: {[e.name for e in entities]}")
    logger.info("-" * 60)
    
    try:
        result = await engine.run_simulation(
            simulation_id=simulation_id,
            proposition=proposition,
            entities=entities,
            max_rounds=2
        )
        
        logger.info(f"\n推演完成! 状态: {result.status.value}")
        logger.info(f"实际参与实体: {[e.name for e in result.entities]}")
        
        return result
        
    except Exception as e:
        logger.error(f"推演失败: {e}")
        raise


async def interactive_debug():
    """交互式调试模式"""
    logger.info("\n" + "=" * 60)
    logger.info("交互式调试模式")
    logger.info("=" * 60)
    
    print("\n请输入推演命题 (直接回车使用默认):")
    proposition = input("> ").strip()
    if not proposition:
        proposition = "台海爆发军事冲突，美国宣布介入"
        print(f"使用默认命题: {proposition}")
    
    print("\n请输入最大推演轮数 (默认 3):")
    max_rounds_input = input("> ").strip()
    max_rounds = int(max_rounds_input) if max_rounds_input.isdigit() else 3
    
    print("\n是否使用预定义实体? (y/n, 默认 n):")
    use_entities = input("> ").strip().lower() == "y"
    
    entities = None
    if use_entities:
        from app.domain.entities import GeopoliticalEntity, EntityType
        entities = [
            GeopoliticalEntity(name="中国", entity_type=EntityType.SOVEREIGN_STATE),
            GeopoliticalEntity(name="美国", entity_type=EntityType.SOVEREIGN_STATE),
            GeopoliticalEntity(name="台湾", entity_type=EntityType.SOVEREIGN_STATE),
        ]
        print(f"使用预定义实体: {[e.name for e in entities]}")
    
    print("\n开始推演...\n")
    
    from app.domain.services import SimulationEngine
    from app.infrastructure.external.llm import LLMFactory
    
    llm = LLMFactory.create(temperature=0.5)
    engine = SimulationEngine(llm)
    
    simulation_id = f"debug_interactive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        result = await engine.run_simulation(
            simulation_id=simulation_id,
            proposition=proposition,
            entities=entities,
            max_rounds=max_rounds
        )
        
        print("\n" + "=" * 60)
        print("推演结果")
        print("=" * 60)
        print(f"状态: {result.status.value}")
        
        if result.status.value == "failed":
            print(f"错误: {result.error_message}")
            return
        
        print(f"实体: {[e.name for e in result.entities]}")
        print(f"轮数: {len(result.rounds)}")
        
        if result.final_report:
            print(f"\n报告摘要:\n{result.final_report[:1000]}...")
        
    except Exception as e:
        logger.error(f"推演失败: {e}")
        import traceback
        print(traceback.format_exc())


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="推演引擎调试工具")
    parser.add_argument(
        "--mode",
        choices=["decision", "simulation", "custom", "interactive", "all"],
        default="all",
        help="调试模式"
    )
    
    args = parser.parse_args()
    
    # 检查环境
    from app.config import settings
    logger.info(f"环境: {settings.APP_ENV}")
    logger.info(f"数据库: {settings.DATABASE_URL}")
    logger.info(f"LLM: {settings.OPENAI_MODEL if settings.OPENAI_API_KEY else 'Not configured'}")
    
    if not settings.OPENAI_API_KEY and not settings.DEEPSEEK_API_KEY and not settings.SILICONFLOW_API_KEY:
        logger.warning("警告: 未配置任何 LLM API Key!")
        logger.warning("请设置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY 或 SILICONFLOW_API_KEY")
        return
    
    # 执行测试
    try:
        if args.mode == "decision" or args.mode == "all":
            await test_decision_engine()
        
        if args.mode == "simulation" or args.mode == "all":
            await test_simulation_engine()
        
        if args.mode == "custom":
            await test_with_custom_entities()
        
        if args.mode == "interactive":
            await interactive_debug()
            
    except Exception as e:
        logger.error(f"调试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    logger.info("\n调试完成!")


if __name__ == "__main__":
    asyncio.run(main())
