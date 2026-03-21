# 地缘政治推演系统 - 完整手册

**版本**: v0.1 MVP  
**日期**: 2026-03-10  
**状态**: 开发就绪  

---

## 目录

1. [产品概述](#1-产品概述)
2. [系统架构](#2-系统架构)
3. [核心流程](#3-核心流程)
4. [功能模块](#4-功能模块)
5. [数据模型](#5-数据模型)
6. [API设计](#6-api设计)
7. [技术栈](#7-技术栈)
8. [项目结构](#8-项目结构)
9. [开发计划](#9-开发计划)
10. [部署指南](#10-部署指南)

---

## 1. 产品概述

### 1.1 产品定位

**"全球地缘政治推演沙盒"** - 一个基于多Agent技术的战略推演系统，帮助用户理解复杂国际事件的连锁反应。

### 1.2 核心价值主张

**不是预测未来，而是"预演可能性"**——让用户在零风险环境中探索：
- 如果事件X发生，各主要行为体（国家、组织）可能如何反应？
- 这些反应会在短期（1-3个月）、中期（6-12个月）、长期（1-3年）产生什么连锁效应？
- 经济、军事、外交、舆论四个维度如何相互影响？

### 1.3 关键特性

| 特性 | 说明 |
|------|------|
| **情报驱动** | 用户只需输入命题，系统自动收集信息、识别相关方 |
| **动态Agent构建** | 根据事件自动构建相关实体Agent（国家、组织、武装团体） |
| **多维度分析** | 经济、军事、外交、舆论四个维度并行分析 |
| **多时间尺度** | 短期（1-3月）、中期（6-12月）、长期（1-3年）推演 |
| **红队挑战** | 自动质疑推演假设，指出盲点 |

### 1.4 目标用户

| 用户类型 | 使用场景 | 核心需求 |
|---------|---------|---------|
| 智库研究员 | 撰写政策建议报告 | 快速生成多维度情景分析 |
| 战略咨询顾问 | 企业地缘政治风险评估 | 理解供应链、市场的潜在冲击 |
| 国际关系学者 | 教学与学术研究 | 可视化复杂系统的非线性特征 |
| 政府分析师 | 政策制定支持 | 识别盲点、挑战既有假设 |
| 金融分析师 | 投资决策支持 | 评估地缘政治对资产价格的影响 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         地缘政治推演系统 v0.1                              │
│                             Tactiq Sandbox                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│    信息收集层        │  │    推演分析层        │  │    可视化展示层      │
│  Intelligence Layer │  │  Simulation Layer   │  │  Visualization Layer│
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│ • 多源信息聚合       │  │ • 动态Agent构建     │  │ • 时空推演图谱       │
│ • 实体识别          │  │ • 多Agent推演引擎    │  │ • 多时间尺度视图     │
│ • 态势理解          │  │ • 红队挑战机制       │  │ • 行为体视角切换     │
│ • 关系网络分析       │  │ • 综合评估          │  │ • 报告生成导出       │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

### 2.2 数据流架构

```
用户输入命题
    │
    ▼
┌─────────────────────────┐
│  第一步：情报收集        │
│  - 多源数据检索          │
│  - 事件背景分析          │
│  - 相关实体识别          │
│  - 立场关系梳理          │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  第二步：动态Agent构建   │
│  - 根据识别的实体        │
│  - 从模板库加载画像      │
│  - 注入当前态势信息      │
│  - 初始化记忆和关系      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  第三步：多Agent推演     │
│  - Orchestrator协调      │
│  - 各Agent基于态势决策   │
│  - 生成连锁反应路径      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  第四步：红队挑战        │
│  - 质疑假设              │
│  - 指出盲点              │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  第五步：综合评估        │
│  - 整合路径              │
│  - 概率评估              │
│  - 监控指标              │
└─────────────────────────┘
```

### 2.3 技术架构

```
用户界面 (React + TypeScript)
    │
    ▼
API Gateway (FastAPI)
    │
    ├──▶ 信息收集服务 (Python)
    │      ├── 数据源适配器 (GDELT/NewsAPI/ACLED)
    │      ├── 实体识别模块 (LLM-based)
    │      └── 态势分析模块
    │
    ├──▶ 推演引擎服务 (Python + LangGraph)
    │      ├── Agent工厂 (动态构建)
    │      ├── 推演控制器 (Orchestrator)
    │      ├── 多Agent工作流
    │      └── 红队挑战
    │
    └──▶ 可视化服务
           └── 图谱渲染引擎

数据存储
    ├── PostgreSQL (结构化数据)
    ├── Redis (缓存/消息队列)
    └── 对象存储 (报告/图谱快照)
```

---

## 3. 核心流程

### 3.1 完整用户旅程

```
[首页]
  │
  ▼
[输入命题]
  │ 用户输入地缘政治事件命题
  │ 例如："美国出兵伊朗的推演"
  ▼
[情报收集中...]
  │ 系统从多源收集信息
  │ 识别相关实体和关系
  │ (预计 3-5 分钟)
  ▼
[Agent构建中...]
  │ 根据识别的实体
  │ 动态构建相关Agent
  │ (预计 1-2 分钟)
  ▼
[推演分析中...]
  │ 多Agent并行推演
  │ 生成连锁反应路径
  │ (预计 2-3 分钟)
  ▼
[推演结果页]
  │ 展示因果图谱
  │ 支持多维度探索
  ▼
[导出/分享]
  │ 生成报告或分享链接
```

### 3.2 示例场景："美国出兵伊朗推演"

#### Step 1: 情报收集输出

```json
{
  "event": "美国宣布向霍尔木兹海峡增派航母战斗群",
  "timeframe": "2026年3月",
  "background": "伊朗威胁封锁海峡作为对以色列袭击核设施的回应",
  
  "identified_entities": [
    {"name": "美国", "role": "initiator", "relevance": 1.0},
    {"name": "伊朗", "role": "target", "relevance": 1.0},
    {"name": "以色列", "role": "key_ally", "relevance": 0.9},
    {"name": "沙特", "role": "regional_ally", "relevance": 0.8},
    {"name": "俄罗斯", "role": "external_power", "relevance": 0.7},
    {"name": "中国", "role": "external_power", "relevance": 0.6},
    {"name": "真主党", "role": "proxy_actor", "relevance": 0.7},
    {"name": "哈马斯", "role": "secondary_actor", "relevance": 0.5},
    {"name": "胡塞武装", "role": "proxy_actor", "relevance": 0.6}
  ],
  
  "relationship_dynamics": {
    "active_conflicts": [
      ["以色列", "哈马斯"],
      ["以色列", "真主党"]
    ],
    "tensions": [
      ["美国", "伊朗"],
      ["沙特", "伊朗"],
      ["俄罗斯", "美国"]
    ],
    "cooperation": [
      ["美国", "以色列"],
      ["美国", "沙特"],
      ["伊朗", "真主党"],
      ["伊朗", "哈马斯"],
      ["伊朗", "胡塞武装"],
      ["俄罗斯", "伊朗"]
    ]
  }
}
```

#### Step 2: Agent工厂构建

根据情报识别的实体，工厂创建对应Agent：

| Agent | 角色 | 注入的当前态势 |
|-------|------|----------------|
| USAAgent | 发起方 | 正在增兵中东，保持外交渠道 |
| IranAgent | 目标方 | 威胁封锁海峡，准备抵抗 |
| IsraelAgent | 关键盟友 | 高度戒备，情报共享 |
| SaudiAgent | 地区盟友 | 担忧卷入冲突，谨慎支持 |
| RussiaAgent | 外部大国 | 谴责美国挑衅，支持伊朗 |
| ChinaAgent | 外部大国 | 呼吁克制，保护能源供应 |
| HezbollahAgent | 代理人 | 准备响应伊朗号召 |
| HamasAgent | 次要参与者 | 观望局势，寻求机会 |
| HouthisAgent | 代理人 | 威胁袭击红海船只 |

#### Step 3: 推演过程

```
Round 1:
- 美国Agent: "继续增兵，同时保持外交渠道开放"
- 伊朗Agent: "宣布部分封锁海峡，但不完全关闭"
- 以色列Agent: "提升防空警戒级别"
- 真主党Agent: "向戈兰高地增兵，威慑以色列"
- 胡塞武装Agent: "警告可能袭击过往油轮"

Round 2:
- 美国: 与盟友协调立场
- 伊朗: 寻求俄罗斯和中国支持
- 真主党: 发射火箭弹试探以色列反应
- 胡塞武装: 实际袭击一艘商船

Round 3:
- 美国: 考虑有限军事打击
- 伊朗: 威胁全面封锁
- 国际社会: 呼吁克制
...
```

---

## 4. 功能模块

### 4.1 信息收集层

#### 4.1.1 数据源矩阵

| 数据源 | 类型 | 覆盖范围 | 语言 | 更新频率 | 接入方式 |
|-------|------|---------|------|---------|---------|
| **GDELT** | 全球事件数据库 | 全球100+国家 | 多语言 | 实时 | BigQuery API |
| **NewsAPI** | 国际新闻聚合 | 全球主流媒体 | 多语言 | 实时 | REST API |
| **ACLED** | 武装冲突数据 | 全球冲突热点 | 英语 | 周更 | API/CSV下载 |
| **Reuters** | 财经新闻 | 全球市场 | 英语 | 实时 | 商业API |

#### 4.1.2 情报收集器

```python
class IntelligenceCollector:
    async def collect(self, event_description: str) -> IntelligenceReport:
        """
        收集情报并生成结构化报告
        
        步骤：
        1. 多源数据检索
        2. 实体识别与关系分析
        3. 态势理解
        4. 整合为情报报告
        """
```

#### 4.1.3 实体识别

使用LLM从文本中自动识别：
- 参与实体（国家、组织、武装团体）
- 各方角色（发起方、目标方、盟友、代理人）
- 当前行动和表态
- 关系网络（盟友、对手、复杂关系）

### 4.2 推演分析层

#### 4.2.1 Agent工厂

```python
class AgentFactory:
    def create_agents(self, intelligence: IntelligenceReport) -> List[EntityAgent]:
        """
        根据情报报告动态创建Agent列表
        
        步骤：
        1. 从模板库加载基础画像
        2. 注入当前态势信息
        3. 初始化记忆和关系
        4. 创建Agent实例
        """
```

**Agent模板库**：

| 实体 | 类型 | 核心属性 | 决策特点 |
|------|------|----------|----------|
| 美国 | 主权国家 | 全球霸权、联盟体系 | 联盟协调、经济制裁优先 |
| 中国 | 主权国家 | 崛起大国、战略耐心 | 长期规划、底线思维 |
| 俄罗斯 | 主权国家 | 军事投射、能源武器 | 地缘博弈、反制果断 |
| 伊朗 | 主权国家 | 地区影响力、代理人网络 | 代理人策略、非对称对抗 |
| 以色列 | 主权国家 | 安全焦虑、技术先进 | 先发制人、情报驱动 |
| 哈马斯 | 非国家武装 | 生存优先、民意基础 | 非对称战术、舆论战 |
| 真主党 | 非国家武装 | 伊朗代理人、军事能力 | 代理人角色、火箭弹威慑 |
| 胡塞武装 | 非国家武装 | 也门内战、红海控制 | 非对称作战、区域干扰 |

#### 4.2.2 Agent基类

```python
class EntityAgent(ABC):
    """
    地缘政治实体Agent基类
    每个实体（国家、组织、武装团体）都是独立Agent
    """
    
    def __init__(self, entity_id: str, entity_profile: Dict):
        self.entity_id = entity_id
        self.profile = entity_profile
        self.memory = AgentMemory()
        self.state = {...}
    
    @abstractmethod
    def perceive(self, event: Dict, context: Dict) -> Perception:
        """感知阶段：理解事件对自身的意义"""
        pass
    
    @abstractmethod
    def decide(self, perception: Perception, 
               available_actions: List[Action],
               other_agents_states: Dict) -> Decision:
        """决策阶段：选择应对策略"""
        pass
    
    @abstractmethod
    def act(self, decision: Decision) -> Action:
        """行动阶段：执行决策"""
        pass
```

#### 4.2.3 推演控制器

```python
class SimulationOrchestrator:
    async def run_simulation(self, event_description: str) -> SimulationResult:
        """
        运行完整推演流程
        
        步骤：
        1. 情报收集
        2. 动态构建Agent
        3. 初始化推演环境
        4. 多轮推演
        5. 红队挑战
        6. 综合评估
        """
```

#### 4.2.4 多维度分析

每个推演节点从四个维度分析：

| 维度 | 关注点 |
|------|--------|
| **经济** | 贸易、投资、供应链、市场 |
| **军事** | 军备、部署、演习、冲突 |
| **外交** | 联盟、制裁、谈判、斡旋 |
| **舆论** | 国内舆论、国际舆论、媒体叙事 |

#### 4.2.5 多时间尺度

| 时间尺度 | 范围 | 关注重点 |
|---------|------|---------|
| **短期** | 1-3个月 | 即时反应、危机管理、舆论战 |
| **中期** | 6-12个月 | 政策调整、经济影响、外交博弈 |
| **长期** | 1-3年 | 结构性变化、联盟重组、格局演变 |

### 4.3 可视化展示层

#### 4.3.1 时空推演图谱

- 节点：事件/行动
- 连线：因果关系
- 时间轴：短期/中期/长期切换
- 多维度筛选：经济/军事/外交/舆论

#### 4.3.2 多视角切换

- 全局视角：所有行为体的互动关系
- 单一行为体视角：该实体的利益、选项、风险评估

#### 4.3.3 报告生成

- 推演路径概览
- 红队挑战清单
- 关键不确定性
- 监控指标建议

---

## 5. 数据模型

### 5.1 核心模型

#### Entity（实体）

```python
class Entity(BaseModel):
    id: UUID
    name: str
    name_en: Optional[str]
    entity_type: EntityType  # sovereign_state, non_state_armed, etc.
    attributes: Dict  # 经济实力、军事实力等
    core_interests: List[str]
    relationships: Dict  # allies, adversaries, complex
    agent_config: Dict  # Agent配置
```

#### IntelligenceReport（情报报告）

```python
class IntelligenceReport(BaseModel):
    event_summary: str
    timeframe: str
    background: str
    identified_entities: List[EntityIdentification]
    relationship_dynamics: RelationshipDynamics
    military_deployments: List[MilitaryDeployment]
    diplomatic_activities: List[DiplomaticActivity]
    economic_measures: List[Dict]
```

#### SimulationResult（推演结果）

```python
class SimulationResult(BaseModel):
    simulation_id: str
    event_id: str
    participating_agents: List[str]
    rounds: List[RoundResult]
    paths: List[SimulationPath]
    red_team_challenges: List[RedTeamChallenge]
    synthesis: Synthesis
```

---

## 6. API设计

### 6.1 核心API

#### 启动推演

```http
POST /api/v1/simulation/run
Content-Type: application/json

{
  "event_description": "美国出兵伊朗的推演",
  "config": {
    "max_rounds": 5,
    "scenarios": ["cooperative", "confrontational", "mixed"]
  }
}

Response:
{
  "id": "uuid",
  "status": "running",
  "message": "推演已启动"
}
```

#### 获取推演结果

```http
GET /api/v1/simulation/{simulation_id}

Response:
{
  "id": "uuid",
  "status": "completed",
  "result": {
    "paths": [...],
    "challenges": [...],
    "synthesis": {...}
  }
}
```

#### 收集情报（独立API）

```http
POST /api/v1/intelligence/collect
Content-Type: application/json

{
  "event_description": "美国宣布对伊朗实施新制裁",
  "time_range": "past_30_days",
  "sources": ["gdelt", "newsapi"]
}

Response:
{
  "task_id": "task_12345",
  "status": "processing",
  "estimated_time": 180
}
```

---

## 7. 技术栈

### 7.1 后端

| 组件 | 技术 | 版本 |
|------|------|------|
| Web框架 | FastAPI | 0.110+ |
| Python | Python | 3.11+ |
| Agent框架 | LangGraph | 0.0.26+ |
| LLM客户端 | OpenAI SDK / Anthropic | 1.12+ / 0.18+ |
| 数据库 | PostgreSQL | 15+ |
| ORM | SQLAlchemy | 2.0+ |
| 缓存 | Redis | 7+ |
| 任务队列 | Celery | 5.3+ |

### 7.2 前端

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | React | 18+ |
| 语言 | TypeScript | 5+ |
| 构建工具 | Vite | 5+ |
| 状态管理 | Zustand | 4+ |
| UI组件 | Ant Design | 5+ |
| 可视化 | React Flow + D3.js | 11+ / 7+ |

### 7.3 部署

| 组件 | 技术 |
|------|------|
| 容器化 | Docker |
| 编排 | Docker Compose |
| 反向代理 | Nginx |

---

## 8. 项目结构

```
geopolitical-simulation/
├── backend/
│   ├── app/
│   │   ├── api/v1/              # API路由
│   │   │   ├── simulation.py    # 推演API
│   │   │   ├── intelligence.py  # 情报API
│   │   │   ├── entities.py      # 实体API
│   │   │   └── reports.py       # 报告API
│   │   ├── models/              # 数据库模型
│   │   ├── schemas/             # Pydantic模型
│   │   │   ├── entity.py
│   │   │   ├── event.py
│   │   │   └── simulation.py
│   │   ├── services/
│   │   │   ├── intelligence/    # 情报收集
│   │   │   │   └── collector.py
│   │   │   └── simulation/      # 推演引擎
│   │   │       ├── agents/
│   │   │       │   ├── base.py           # Agent基类
│   │   │       │   ├── factory.py        # Agent工厂
│   │   │       │   └── entities/         # 实体Agent
│   │   │       │       ├── usa.py
│   │   │       │       ├── hamas.py
│   │   │       │       └── ...
│   │   │       └── orchestrator.py       # 推演控制器
│   │   ├── db/                  # 数据库
│   │   ├── tasks/               # Celery任务
│   │   ├── main.py              # FastAPI入口
│   │   └── config.py            # 配置管理
│   ├── requirements.txt
│   └── docker/Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # 组件
│   │   ├── pages/               # 页面
│   │   ├── stores/              # 状态管理
│   │   └── services/            # API服务
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## 9. 开发计划

### Phase 1: 基础架构 (Week 1-2)

**目标**: 搭建项目骨架，实现基础API

**任务清单**:
- [ ] 初始化项目结构
- [ ] 配置Docker开发环境
- [ ] 实现数据库模型
- [ ] 搭建FastAPI框架
- [ ] 配置日志和异常处理

**交付物**:
- 可运行的后端服务
- 基础API文档

---

### Phase 2: 情报收集模块 (Week 3-4)

**目标**: 实现多源情报收集和实体识别

**任务清单**:
- [ ] 集成GDELT数据源
- [ ] 集成NewsAPI数据源
- [ ] 实现实体识别（LLM-based）
- [ ] 实现关系网络分析
- [ ] 实现态势理解
- [ ] 编写情报收集API

**交付物**:
- 情报收集器
- 实体识别API
- 示例情报报告

---

### Phase 3: Agent系统 (Week 5-7)

**目标**: 实现Agent工厂和核心实体Agent

**任务清单**:
- [ ] 实现Agent基类
- [ ] 实现Agent工厂
- [ ] 创建Agent模板库（10个核心实体）
  - [ ] 美国Agent
  - [ ] 中国Agent
  - [ ] 俄罗斯Agent
  - [ ] 伊朗Agent
  - [ ] 以色列Agent
  - [ ] 沙特Agent
  - [ ] 哈马斯Agent
  - [ ] 真主党Agent
  - [ ] 胡塞武装Agent
  - [ ] 欧盟Agent
- [ ] 实现Agent记忆系统
- [ ] 测试Agent决策逻辑

**交付物**:
- Agent工厂
- 10个实体Agent实现
- Agent测试用例

---

### Phase 4: 推演引擎 (Week 8-9)

**目标**: 实现推演控制器和多轮推演

**任务清单**:
- [ ] 实现推演控制器（Orchestrator）
- [ ] 实现多轮推演逻辑
- [ ] 实现Agent交互机制
- [ ] 实现红队挑战Agent
- [ ] 实现综合评估Agent
- [ ] 实现推演结果提取

**交付物**:
- 推演引擎
- 推演API
- 示例推演结果

---

### Phase 5: 可视化前端 (Week 10-11)

**目标**: 实现前端界面和可视化

**任务清单**:
- [ ] 搭建React项目
- [ ] 实现首页和事件输入
- [ ] 实现推演状态展示
- [ ] 实现因果图谱（React Flow）
- [ ] 实现多时间尺度切换
- [ ] 实现多维度筛选
- [ ] 实现报告展示
- [ ] 实现导出功能

**交付物**:
- 前端应用
- 可视化组件

---

### Phase 6: 集成测试 (Week 12)

**目标**: 端到端测试和优化

**任务清单**:
- [ ] 端到端测试
- [ ] 性能优化
- [ ] Bug修复
- [ ] 文档完善
- [ ] 部署准备

**交付物**:
- 完整系统
- 测试报告
- 部署文档

---

## 10. 部署指南

### 10.1 环境要求

- Docker 24+
- Docker Compose 2+
- 4GB+ RAM
- 10GB+ 磁盘空间

### 10.2 快速启动

```bash
# 1. 克隆项目
git clone <repository-url>
cd geopolitical-simulation

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置API密钥

# 3. 启动服务
docker-compose up -d

# 4. 访问服务
# 前端: http://localhost:3000
# API: http://localhost:8000
# 文档: http://localhost:8000/docs
```

### 10.3 环境变量

```bash
# LLM API（至少配置一个）
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...

# 数据源（可选，用于增强情报收集）
NEWSAPI_KEY=...
ACLED_API_KEY=...
```

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| **推演** | 基于假设的情景分析，非预测 |
| **Agent** | 具有自主决策能力的实体模型 |
| **情报** | 从多源收集的结构化信息 |
| **路径** | 一系列连锁反应的推演结果 |
| **红队** | 专门挑战假设的分析角色 |

### B. 参考资源

- [BettaFish](https://github.com/666ghj/BettaFish)
- [MiroFish](https://github.com/666ghj/MiroFish)
- [GDELT Project](https://www.gdeltproject.org/)
- [ACLED](https://acleddata.com/)

# 快速使用
## 运行前端
```
cd frontend 
npm install
npm run dev
```
## 运行后端
```
cd /root/fudong/Tactiq
cp .env.example .env

# 2. 编辑 .env，配置至少一个 LLM API Key
# 推荐使用 DeepSeek（性价比高）
vi .env

# 3. 只启动数据库和缓存服务
docker compose up -d postgres redis

# 4. 本地启动后端（便于开发调试）
cd backend

# 创建 Python 虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动后端
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

**文档版本**: v0.1  
**最后更新**: 2026-03-10  
**作者**: Fudong
