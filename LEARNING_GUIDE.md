# Tactiq 项目学习指南

## 项目概述

Tactiq 是一个基于领域驱动设计(DDD)的地缘政治推演系统，使用 FastAPI + LangGraph 构建。

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      API 层 (Interface)                      │
│                    FastAPI 路由 + Schema                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   应用服务层 (Application)                    │
│              用例编排 + 事务管理 + 事件发布                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      领域层 (Domain)                         │
│              实体 + 值对象 + 领域事件 + 领域服务               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   基础设施层 (Infrastructure)                 │
│         仓储实现 + 外部服务适配器(LLM/数据库/缓存)              │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
backend/app/
├── api/v1/              # API路由层
│   ├── simulation.py    # 推演接口
│   ├── intelligence.py  # 情报接口
│   └── ...
├── application/         # 应用服务层
│   ├── simulation_service.py
│   └── intelligence_service.py
├── domain/              # 领域层
│   ├── entities/        # 领域实体
│   │   ├── geopolitical_entity.py
│   │   └── value_objects.py
│   └── events/          # 领域事件
│       ├── event_bus.py
│       └── simulation_events.py
├── infrastructure/      # 基础设施层
│   ├── external/llm/    # LLM适配器
│   └── repositories/    # 仓储实现
├── core/                # 核心组件
│   ├── container.py     # 依赖注入容器
│   └── redis_client.py  # Redis客户端
├── db/                  # 数据库配置
├── models/              # ORM模型
└── main.py              # 应用入口
```

## 学习路径

### 第一阶段：理解领域模型 (2-3天)

1. **阅读领域实体**
   - `app/domain/entities/geopolitical_entity.py`
   - `app/domain/entities/value_objects.py`
   
   理解：
   - 什么是领域实体？与ORM模型的区别
   - 值对象的特点（不可变性）
   - 实体的业务行为方法

2. **理解领域事件**
   - `app/domain/events/event_bus.py`
   - `app/domain/events/simulation_events.py`
   
   理解：
   - 领域事件的作用（解耦、可观测）
   - 事件总线的工作原理
   - 如何发布和订阅事件

**练习**：
- 添加一个新的领域事件 `EntityRoleChanged`
- 实现一个订阅该事件的处理器，打印日志

### 第二阶段：掌握基础设施 (2-3天)

1. **LLM Provider 适配器**
   - `app/infrastructure/external/llm/provider.py`
   - `app/infrastructure/external/llm/factory.py`
   
   理解：
   - 适配器模式的作用
   - 如何添加新的LLM提供商
   - 统一接口的好处

2. **仓储模式**
   - `app/infrastructure/repositories/base.py`
   - `app/infrastructure/repositories/simulation_repository.py`
   
   理解：
   - 仓储接口与实现的分离
   - 为什么要隔离数据访问
   - 如何测试仓储层

**练习**：
- 添加一个新的 LLM Provider（如 Anthropic）
- 为 Event 实体创建仓储接口和实现

### 第三阶段：应用服务层 (2天)

1. **应用服务**
   - `app/application/simulation_service.py`
   - `app/application/intelligence_service.py`
   
   理解：
   - 应用服务的职责边界
   - 如何协调领域对象
   - 事务管理的位置

2. **依赖注入**
   - `app/core/container.py`
   
   理解：
   - 控制反转(IoC)的概念
   - 依赖注入的好处
   - 容器的生命周期管理

**练习**：
- 创建一个新的应用服务 `ReportApplicationService`
- 在容器中注册该服务

### 第四阶段：API层 (1-2天)

1. **FastAPI 路由**
   - `app/api/v1/simulation.py`
   - `app/api/v1/intelligence.py`
   
   理解：
   - 依赖注入在FastAPI中的使用
   - 请求/响应模型定义
   - 错误处理

**练习**：
- 添加一个新的API端点 `/api/v1/simulation/{id}/export`
- 实现导出推演结果为JSON的功能

### 第五阶段：LangGraph 推演引擎 (3-4天) ⭐核心

1. **决策引擎 - 鹰鸽辩论机制**
   - `app/domain/services/decision_engine.py`
   
   理解：
   - 鹰派顾问 (`_hawk_advisor`): 主张激进/对抗策略
   - 鸽派顾问 (`_dove_advisor`): 主张克制/外交策略  
   - 最终决策者 (`_final_decision`): 综合双方观点
   - 决策维度: Military/Diplomatic/Economic/Energy/PublicOpinion
   
   关键代码：
   ```python
   async def make_decision(entity, context) -> DecisionResult:
       hawk = await self._hawk_advisor(entity, context)
       dove = await self._dove_advisor(entity, context, hawk)
       return await self._final_decision(entity, context, hawk, dove)
   ```

2. **推演引擎 - LangGraph 四阶段流水线**
   - `app/domain/services/simulation_engine.py`
   
   理解：
   - **Phase 1**: Entity Identification - LLM识别相关实体
   - **Phase 2**: Entity Profiling - 构建实体政治画像
   - **Phase 3**: Game Coordination - 多轮博弈推演
   - **Phase 4**: Synthesis - 生成综合报告
   
   LangGraph 状态图：
   ```python
   workflow = StateGraph(SimulationState)
   workflow.add_node("identify_entities", self._identify_entities)
   workflow.add_node("profile_entities", self._profile_entities)
   workflow.add_node("coordinate_game", self._coordinate_game)
   workflow.add_node("synthesize", self._synthesize)
   ```

3. **应用服务协调**
   - `app/application/simulation_service.py`
   
   理解：
   - `start_simulation()`: 创建推演任务
   - `execute_simulation()`: 调用 LangGraph 引擎执行
   - 发布领域事件: SimulationStarted/RoundCompleted/SimulationCompleted

**练习**：
- 修改鹰鸽辩论的提示词模板，观察决策变化
- 添加一个新的决策维度 (如 Cyber 网络战)
- 实现推演结果的自定义格式化
- 添加收敛检测：当局势稳定时提前结束推演

### 第六阶段：调试与测试 (持续)

1. **调试技巧**
   - 使用 `loguru` 记录日志
   - 在领域事件中添加断点
   - 使用 `/docs` 测试API

2. **测试策略**
   - 单元测试：测试领域实体
   - 集成测试：测试仓储层
   - API测试：测试端点

## 调试指南

### 1. 启动调试模式

```bash
cd backend
export APP_ENV=development
export DEBUG=true
python start.py
```

### 2. 使用 API 文档调试

访问 `http://localhost:8000/docs`

- 可以直接测试所有API端点
- 查看请求/响应模型
- 复制curl命令

### 3. 查看日志

```bash
# 实时查看日志
tail -f backend/logs/app.log

# Docker环境
docker-compose logs -f backend
```

### 4. 数据库调试

```bash
# 连接PostgreSQL
docker-compose exec postgres psql -U user -d geopolitics

# 查看表结构
\dt
\d simulation

# 查询数据
SELECT * FROM simulation LIMIT 5;
```

### 5. Redis调试

```bash
# 连接Redis
docker-compose exec redis redis-cli

# 查看键
KEYS tactiq:*

# 查看任务状态
GET tactiq:task:simulation:<id>
```

### 6. 断点调试 (VS Code)

创建 `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["app.main:app", "--reload"],
            "jinja": true,
            "justMyCode": true,
            "cwd": "${workspaceFolder}/backend"
        }
    ]
}
```

## 常见问题

### Q: 如何添加新的领域实体？

A: 
1. 在 `app/domain/entities/` 创建实体文件
2. 定义实体的属性和业务方法
3. 创建对应的仓储接口和实现
4. 在应用服务中使用

### Q: 如何切换LLM提供商？

A:
1. 在 `.env` 中配置对应的API Key
2. LLMFactory会自动选择可用的Provider
3. 优先级：OpenAI > DeepSeek > SiliconFlow

### Q: 如何发布领域事件？

A:
```python
from app.domain.events import event_bus, SimulationStarted

await event_bus.publish(
    SimulationStarted(simulation_id="xxx", proposition="...")
)
```

### Q: 如何订阅领域事件？

A:
```python
from app.domain.events import event_bus, SimulationStarted

async def on_simulation_started(event: SimulationStarted):
    print(f"推演开始: {event.proposition}")

event_bus.subscribe(SimulationStarted, on_simulation_started)
```

## 推荐学习资源

### 领域驱动设计 (DDD)
- 《领域驱动设计》Eric Evans
- 《实现领域驱动设计》Vaughn Vernon

### FastAPI
- 官方文档: https://fastapi.tiangolo.com/
- 中文文档: https://fastapi.tiangolo.com/zh/

### 架构模式
- 适配器模式 (Adapter Pattern)
- 仓储模式 (Repository Pattern)
- 依赖注入 (Dependency Injection)
- 事件驱动架构 (Event-Driven Architecture)

## 项目启动步骤

```bash
# 1. 克隆项目
git clone <repository>
cd Tactiq

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env 文件，添加你的API Keys

# 3. 启动服务
./start.sh
# 选择选项 1 (Docker Compose)

# 4. 访问服务
# API: http://localhost:8000
# 文档: http://localhost:8000/docs
# 前端: http://localhost:3000
```

## 下一步建议

1. **阅读代码**: 按学习路径顺序阅读代码
2. **动手实践**: 完成每个阶段的练习
3. **添加功能**: 尝试添加一个小功能
4. **编写测试**: 为新增功能编写测试
5. **代码审查**: 与团队成员讨论架构设计

祝你学习愉快！
