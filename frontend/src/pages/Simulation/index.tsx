import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Card, Spin, Alert, Steps, Typography, List, Tag, Progress, Collapse, Tabs, Radio } from 'antd'
import { LoadingOutlined, CheckCircleOutlined, ClockCircleOutlined, EyeOutlined, HistoryOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import CausalGraph from '../../components/CausalGraph'
import SimulationWorkflow from '../../components/SimulationWorkflow'
import ExecutionTimeline from '../../components/ExecutionTimeline'
import RoundVisualization from '../../components/RoundVisualization'
import { useSimulationStore } from '../../stores/simulationStore'
import './style.css'

const { Title, Text } = Typography
const { Panel } = Collapse
const { TabPane } = Tabs

// 实体类型到颜色的映射
const entityTypeColors: Record<string, string> = {
  country: '#5470c6',
  organization: '#91cc75',
  person: '#fac858',
  non_state_actor: '#ee6666',
  international_org: '#73c0de',
  unknown: '#9a60b4'
}

// 角色到图标/形状的映射
const roleShapes: Record<string, string> = {
  initiator: 'diamond',
  target: 'triangle',
  ally: 'circle',
  adversary: 'rect',
  mediator: 'roundRect',
  stakeholder: 'circle',
  unknown: 'circle'
}

function Simulation() {
  const { id } = useParams<{ id: string }>()
  const [loading, setLoading] = useState(true)
  const [currentStep, setCurrentStep] = useState(0)
  const [collectedContents, setCollectedContents] = useState<any[]>([])
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('collecting')
  const [entities, setEntities] = useState<any[]>([])
  const setRelationships = useState<any[]>([])[1]
  const [preEntities, setPreEntities] = useState<any[]>([])  // 预识别实体
  const [, setPreRelationships] = useState<any[]>([])  // 预识别关系
  const [expandedQueries, setExpandedQueries] = useState<any[]>([])  // 扩展查询
  const [simulationResult, setSimulationResult] = useState<any>(null)  // 推演结果（包含因果路径）
  const [error, setError] = useState<string | null>(null)
  const [activeVisualizationTab, setActiveVisualizationTab] = useState('workflow')
  
  // 使用Zustand store获取可视化状态
  const {
    nodeExecutionHistory,
    roundHistory,
    currentNode,
    currentRound,
    visualizationMode,
    setVisualizationMode,
    processExecutionEvent,
    setSimulationStartTime,
    setSimulationEndTime,
    reset: resetVisualization
  } = useSimulationStore()
  
  // 使用ref来跟踪轮询状态，避免闭包问题
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isCompletedRef = useRef(false)
  const wsRef = useRef<WebSocket | null>(null)

  // 轮询获取推演状态
  useEffect(() => {
    // 清除之前的轮询
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    
    // 如果已完成，不再轮询
    if (isCompletedRef.current) {
      return
    }

    const pollData = async () => {
      try {
        // 获取推演状态
        const statusResponse = await fetch(`/api/v1/simulation/${id}`)
        
        if (!statusResponse.ok) {
          if (statusResponse.status === 404) {
            // 任务不存在，后端可能已重启，停止轮询并显示错误
            console.error('Simulation task not found (backend may have restarted)')
            setError('推演任务不存在，请重新创建推演')
            setLoading(false)
            isCompletedRef.current = true
            if (intervalRef.current) {
              clearInterval(intervalRef.current)
              intervalRef.current = null
            }
            return
          }
          throw new Error(`HTTP error! status: ${statusResponse.status}`)
        }
        
        const statusData = await statusResponse.json()
        setProgress(statusData.progress || 0)
        setStatus(statusData.status)
        
        // 根据状态设置当前步骤
        switch (statusData.status) {
          case 'pending':
            setCurrentStep(0)
            break
          case 'collecting':
            setCurrentStep(0)
            break
          case 'building_agents':
            setCurrentStep(1)
            break
          case 'simulating':
            setCurrentStep(2)
            break
          case 'red_teaming':
            setCurrentStep(3)
            break
          case 'evaluating':
            setCurrentStep(4)
            break
          case 'completed':
            setCurrentStep(5)
            setLoading(false)
            isCompletedRef.current = true
            if (intervalRef.current) {
              clearInterval(intervalRef.current)
              intervalRef.current = null
            }
            // 获取推演结果
            if (statusData.result) {
              console.log('Simulation result:', statusData.result)
              console.log('Paths:', statusData.result.paths)
              setSimulationResult(statusData.result)
            } else {
              console.log('No result in statusData:', statusData)
            }
            break
          case 'failed':
            setLoading(false)
            setError(statusData.error || '推演失败')
            isCompletedRef.current = true
            if (intervalRef.current) {
              clearInterval(intervalRef.current)
              intervalRef.current = null
            }
            break
        }
        
        // 获取预识别实体（LLM预识别阶段 - 优先使用，不依赖mock）
        if (statusData.status !== 'pending') {
          try {
            const preEntitiesResponse = await fetch(`/api/v1/intelligence/task/${id}/pre-entities`)
            if (preEntitiesResponse.ok) {
              const preData = await preEntitiesResponse.json()
              if (preData.pre_identified_entities && preData.pre_identified_entities.length > 0) {
                setPreEntities(preData.pre_identified_entities)
              }
              if (preData.pre_identified_relationships && preData.pre_identified_relationships.length > 0) {
                setPreRelationships(preData.pre_identified_relationships)
              }
              if (preData.expanded_queries && preData.expanded_queries.length > 0) {
                setExpandedQueries(preData.expanded_queries)
              }
            }
          } catch (e) {
            console.log('Failed to fetch pre-identified entities:', e)
          }
          
          // 获取最终识别的实体（从文章内容中提取的）
          try {
            const entitiesResponse = await fetch(`/api/v1/intelligence/task/${id}/entities`)
            if (entitiesResponse.ok) {
              const entitiesData = await entitiesResponse.json()
              if (Array.isArray(entitiesData) && entitiesData.length > 0) {
                setEntities(entitiesData)
              }
            }
          } catch (e) {
            console.log('Failed to fetch entities:', e)
          }
        }
        
        // 获取收集到的内容（仅在情报收集阶段）
        if (statusData.status === 'collecting' || statusData.status === 'building_agents') {
          try {
            const contentsResponse = await fetch(`/api/v1/intelligence/task/${id}/contents`)
            if (contentsResponse.ok) {
              const contentsData = await contentsResponse.json()
              if (Array.isArray(contentsData)) {
                setCollectedContents(contentsData)
              }
            }
          } catch (e) {
            // 忽略内容获取错误
          }
        }
      } catch (error) {
        console.error('Failed to fetch simulation status:', error)
        // 不显示错误，继续轮询
      }
    }
    
    // 立即执行一次
    pollData()
    
    // 设置轮询间隔（5秒一次，减少服务器压力）
    intervalRef.current = setInterval(pollData, 5000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [id])

  // WebSocket连接用于实时事件
  useEffect(() => {
    if (!id) return
    
    // 重置可视化状态
    resetVisualization()
    
    // 建立WebSocket连接
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/simulation/${id}`
    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    
    ws.onopen = () => {
      console.log('WebSocket connected for simulation:', id)
    }
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        
        // 处理节点事件和轮次事件
        if (message.type === 'node_event' || message.type === 'round_event') {
          processExecutionEvent(message)
        }
        
        // 处理进度更新
        if (message.type === 'progress' || message.type === 'status') {
          const data = message.data || message
          if (data.status === 'running' && data.started_at) {
            setSimulationStartTime(new Date(data.started_at).getTime())
          }
          if ((data.status === 'completed' || data.status === 'failed') && data.completed_at) {
            setSimulationEndTime(new Date(data.completed_at).getTime())
          }
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [id, resetVisualization, processExecutionEvent, setSimulationStartTime, setSimulationEndTime])

  const getStepStatus = (stepIndex: number) => {
    if (stepIndex < currentStep) return 'finish'
    if (stepIndex === currentStep) return 'process'
    return 'wait'
  }

  // 生成关系图数据
  const generateGraphData = () => {
    if (!entities || entities.length === 0) {
      return { nodes: [], links: [] }
    }

    const nodes = entities.map((entity: any, index: number) => ({
      id: entity.name || `entity_${index}`,
      name: entity.name || 'Unknown',
      symbolSize: Math.max(30, (entity.relevance_score || 0.5) * 60),
      value: entity.relevance_score || 0.5,
      category: entity.entity_type || 'unknown',
      symbol: roleShapes[entity.role] || 'circle',
      itemStyle: {
        color: entityTypeColors[entity.entity_type] || entityTypeColors.unknown
      },
      label: {
        show: true,
        formatter: '{b}',
        fontSize: 12
      },
      // 额外数据
      role: entity.role,
      entityType: entity.entity_type,
      currentActions: entity.current_actions || []
    }))

    // 生成关系链接（基于角色）
    const links: any[] = []
    const initiators = entities.filter((e: any) => e.role === 'initiator')
    const targets = entities.filter((e: any) => e.role === 'target')
    const allies = entities.filter((e: any) => e.role === 'ally')
    const adversaries = entities.filter((e: any) => e.role === 'adversary')

    // 发起者到目标的关系
    initiators.forEach((initiator: any) => {
      targets.forEach((target: any) => {
        links.push({
          source: initiator.name,
          target: target.name,
          value: '冲突',
          lineStyle: {
            color: '#ff4d4f',
            width: 2,
            curveness: 0.2
          }
        })
      })
    })

    // 盟友关系
    allies.forEach((ally: any) => {
      initiators.forEach((initiator: any) => {
        links.push({
          source: ally.name,
          target: initiator.name,
          value: '盟友',
          lineStyle: {
            color: '#52c41a',
            width: 1.5,
            type: 'dashed'
          }
        })
      })
    })

    // 对手关系
    adversaries.forEach((adversary: any) => {
      targets.forEach((target: any) => {
        links.push({
          source: adversary.name,
          target: target.name,
          value: '支持',
          lineStyle: {
            color: '#faad14',
            width: 1.5,
            type: 'dotted'
          }
        })
      })
    })

    return { nodes, links }
  }

  // 关系图配置
  const getGraphOption = () => {
    const { nodes, links } = generateGraphData()
    
    return {
      title: {
        text: '实体关系网络',
        subtext: '节点颜色=实体类型 | 连线颜色=关系类型（红=冲突 绿=盟友 黄=支持）',
        left: 'center',
        top: 10
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            const data = params.data
            const entity = entities.find((e: any) => e.name === data.name)
            if (!entity) return data.name
            
            return `
              <div style="max-width: 350px; padding: 10px;">
                <strong style="font-size: 16px;">${entity.name}</strong>
                ${entity.name_en ? `<span style="color: #999; margin-left: 8px;">${entity.name_en}</span>` : ''}<br/>
                <hr style="margin: 8px 0; border: none; border-top: 1px solid #eee;"/>
                <div style="line-height: 1.8;">
                  <span style="color: #666;">类型:</span> ${entity.entity_type || '未知'}<br/>
                  <span style="color: #666;">角色:</span> ${entity.role || '未知'}<br/>
                  <span style="color: #666;">相关性:</span> ${((entity.relevance_score || 0.5) * 100).toFixed(0)}%<br/>
                  ${entity.rationale ? `<span style="color: #666;">分析依据:</span> ${entity.rationale}<br/>` : ''}
                  ${entity.stated_position ? `<span style="color: #666;">立场:</span> ${entity.stated_position}<br/>` : ''}
                  ${entity.current_actions && entity.current_actions.length > 0 ? 
                    `<span style="color: #666;">当前行动:</span> ${entity.current_actions.join(', ')}<br/>` : ''}
                  ${entity.key_interests && entity.key_interests.length > 0 ? 
                    `<span style="color: #666;">核心利益:</span> ${entity.key_interests.join(', ')}<br/>` : ''}
                </div>
              </div>
            `
          }
          return `${params.data.source} → ${params.data.target}: ${params.data.value}`
        }
      },
      legend: {
        data: Object.keys(entityTypeColors).map(type => ({
          name: type,
          icon: 'circle'
        })),
        bottom: 10,
        textStyle: {
          fontSize: 10
        }
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: links,
          categories: Object.keys(entityTypeColors).map(type => ({ name: type })),
          roam: true,
          draggable: true,
          focusNodeAdjacency: true,
          force: {
            repulsion: 300,
            gravity: 0.1,
            edgeLength: [100, 200],
            layoutAnimation: true
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 4
            }
          },
          lineStyle: {
            color: 'source',
            curveness: 0.3,
            opacity: 0.7
          },
          edgeLabel: {
            show: true,
            formatter: '{c}',
            fontSize: 10
          },
          edgeSymbol: ['circle', 'arrow'],
          edgeSymbolSize: [4, 10]
        }
      ]
    }
  }

  // 地理关系图配置
  const getGeoGraphOption = () => {
    const { nodes, links } = generateGraphData()
    
    // 简化版本，使用散点图模拟地理分布
    return {
      title: {
        text: '地理分布图（示意）',
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}'
      },
      xAxis: {
        show: false,
        min: 0,
        max: 100
      },
      yAxis: {
        show: false,
        min: 0,
        max: 100
      },
      series: [
        {
          type: 'scatter',
          symbolSize: (data: any) => data[2] * 50,
          data: nodes.map((node: any, index: number) => {
            // 根据角色分配大致位置（模拟地理分布）
            let x = 50, y = 50
            if (node.role === 'initiator') {
              x = 20 + Math.random() * 20
              y = 30 + Math.random() * 40
            } else if (node.role === 'target') {
              x = 60 + Math.random() * 20
              y = 30 + Math.random() * 40
            } else if (node.role === 'ally') {
              x = 10 + Math.random() * 15
              y = 20 + Math.random() * 60
            } else {
              x = 30 + Math.random() * 50
              y = 20 + Math.random() * 60
            }
            return {
              name: node.name,
              value: [x, y, node.value],
              itemStyle: {
                color: entityTypeColors[node.category] || entityTypeColors.unknown
              }
            }
          }),
          label: {
            show: true,
            formatter: '{b}',
            position: 'top'
          }
        }
      ]
    }
  }

  const renderContentItem = (item: any, index: number) => {
    // 安全获取字段，防止undefined错误
    const relevanceScore = item?.relevance_score ?? 0
    const sentiment = item?.sentiment ?? 'neutral'
    const title = item?.title ?? '无标题'
    const url = item?.url ?? '#'
    const source = item?.source ?? '未知来源'
    const publishedAt = item?.published_at
    const summary = item?.summary
    const content = item?.content ?? ''
    
    const relevanceColor = relevanceScore >= 0.8 ? 'green' : 
                          relevanceScore >= 0.6 ? 'blue' : 
                          relevanceScore >= 0.4 ? 'orange' : 'red'
    
    const sentimentColor = sentiment === 'positive' ? 'green' :
                          sentiment === 'negative' ? 'red' : 'default'
    
    // 构建显示文本
    let displayText = summary
    if (!displayText && content) {
      displayText = content.substring(0, 200) + (content.length > 200 ? '...' : '')
    }
    if (!displayText) {
      displayText = '暂无内容摘要'
    }

    return (
      <List.Item key={index}>
        <List.Item.Meta
          title={
            <a href={url} target="_blank" rel="noopener noreferrer">
              {title}
            </a>
          }
          description={
            <div style={{ marginTop: 8 }}>
              <div style={{ marginBottom: 8 }}>
                <Tag color="blue">{source}</Tag>
                <Tag color={relevanceColor}>{(relevanceScore * 100).toFixed(0)}%相关</Tag>
                <Tag color={sentimentColor}>{sentiment}</Tag>
                {publishedAt && (
                  <Text type="secondary" style={{ marginLeft: 8 }}>
                    {new Date(publishedAt).toLocaleDateString()}
                  </Text>
                )}
              </div>
              <Text>{displayText}</Text>
            </div>
          }
        />
      </List.Item>
    )
  }

  return (
    <div className="simulation-container">
      <Card>
        <Title level={3}>推演进行中</Title>
        <Text type="secondary">推演ID: {id}</Text>
        
        {loading ? (
          <div className="loading-container">
            <Spin 
              indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} 
              tip="正在进行地缘政治推演..."
            />
            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Progress percent={progress} status="active" />
              <Text type="secondary">进度: {progress}%</Text>
            </div>
          </div>
        ) : (
          <Alert 
            message="推演完成" 
            type="success" 
            icon={<CheckCircleOutlined />}
            showIcon
          />
        )}

        <Steps 
          current={currentStep} 
          direction="vertical" 
          style={{ marginTop: 24 }}
          items={[
            {
              title: '情报收集',
              description: '从多源收集信息，识别相关实体',
              status: getStepStatus(0),
              icon: getStepStatus(0) === 'process' ? <ClockCircleOutlined /> : undefined
            },
            {
              title: 'Agent构建',
              description: '动态构建相关方Agent',
              status: getStepStatus(1)
            },
            {
              title: '推演执行',
              description: '多轮推演，生成连锁反应路径',
              status: getStepStatus(2)
            },
            {
              title: '红队挑战',
              description: '质疑假设，指出盲点',
              status: getStepStatus(3)
            },
            {
              title: '综合评估',
              description: '整合路径，评估概率',
              status: getStepStatus(4)
            }
          ]}
        />

        {/* 错误提示 */}
        {error && (
          <Alert
            message="推演失败"
            description={error}
            type="error"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        {/* 推演流程可视化 */}
        <Card 
          title="推演流程可视化" 
          style={{ marginTop: 24 }}
          extra={
            <Radio.Group 
              value={visualizationMode} 
              onChange={(e) => setVisualizationMode(e.target.value)}
              size="small"
            >
              <Radio.Button value="realtime">
                <EyeOutlined /> 实时
              </Radio.Button>
              <Radio.Button value="summary">
                <HistoryOutlined /> 汇总
              </Radio.Button>
            </Radio.Group>
          }
        >
          <Tabs 
            activeKey={activeVisualizationTab} 
            onChange={setActiveVisualizationTab}
            type="card"
          >
            <TabPane tab="流程图" key="workflow">
              <SimulationWorkflow 
                nodeStates={nodeExecutionHistory}
                currentNode={currentNode}
              />
            </TabPane>
            <TabPane tab="执行时间线" key="timeline">
              <ExecutionTimeline 
                nodeStates={nodeExecutionHistory}
                rounds={roundHistory}
                status={status === 'completed' ? 'completed' : status === 'failed' ? 'error' : 'running'}
                error={error || undefined}
              />
            </TabPane>
            <TabPane tab="推演轮次" key="rounds">
              <RoundVisualization 
                rounds={roundHistory}
                currentRound={currentRound}
              />
            </TabPane>
          </Tabs>
        </Card>

        {/* 实体关系可视化 */}
        {entities.length > 0 && (
          <Card title="识别的实体与关系" style={{ marginTop: 24 }}>
            <Tabs defaultActiveKey="graph">
              <TabPane tab="关系网络图" key="graph">
                <ReactECharts
                  option={getGraphOption()}
                  style={{ height: '500px', width: '100%' }}
                  opts={{ renderer: 'canvas' }}
                />
              </TabPane>
              <TabPane tab="地理分布图" key="geo">
                <ReactECharts
                  option={getGeoGraphOption()}
                  style={{ height: '500px', width: '100%' }}
                  opts={{ renderer: 'canvas' }}
                />
              </TabPane>
              <TabPane tab="实体列表" key="list">
                <List
                  dataSource={entities}
                  renderItem={(entity: any) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <div>
                            <Tag color={entityTypeColors[entity.entity_type] || entityTypeColors.unknown}>
                              {entity.entity_type}
                            </Tag>
                            <Text strong>{entity.name}</Text>
                            {entity.name_en && (
                              <Text type="secondary" style={{ marginLeft: 8 }}>
                                ({entity.name_en})
                              </Text>
                            )}
                          </div>
                        }
                        description={
                          <div style={{ marginTop: 8 }}>
                            <div>
                              <Tag color="blue">角色: {entity.role}</Tag>
                              <Tag color="green">相关性: {(entity.relevance_score * 100).toFixed(0)}%</Tag>
                            </div>
                            {entity.current_actions && entity.current_actions.length > 0 && (
                              <div style={{ marginTop: 8 }}>
                                <Text type="secondary">当前行动: </Text>
                                {entity.current_actions.map((action: string, idx: number) => (
                                  <Tag key={idx}>{action}</Tag>
                                ))}
                              </div>
                            )}
                            {entity.key_interests && entity.key_interests.length > 0 && (
                              <div style={{ marginTop: 4 }}>
                                <Text type="secondary">核心利益: </Text>
                                {entity.key_interests.map((interest: string, idx: number) => (
                                  <Tag key={idx} color="orange">{interest}</Tag>
                                ))}
                              </div>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              </TabPane>
            </Tabs>
          </Card>
        )}

        {/* 预识别实体展示（情报收集阶段早期展示） */}
        {preEntities.length > 0 && (
          <Card 
            title="预识别实体（LLM分析）" 
            style={{ marginTop: 24 }}
            extra={<Tag color="blue">{preEntities.length} 个实体</Tag>}
          >
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              基于推演命题，LLM预识别的可能涉及实体
            </Text>
            <List
              dataSource={preEntities}
              renderItem={(entity: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <div>
                        <Tag color={entityTypeColors[entity.entity_type] || entityTypeColors.unknown}>
                          {entity.entity_type}
                        </Tag>
                        <Text strong>{entity.name}</Text>
                        <Tag color="green" style={{ marginLeft: 8 }}>
                          相关性: {(entity.relevance * 100).toFixed(0)}%
                        </Tag>
                      </div>
                    }
                    description={
                      <div style={{ marginTop: 8 }}>
                        <Tag color="blue">角色: {entity.role}</Tag>
                        {entity.rationale && (
                          <div style={{ marginTop: 8 }}>
                            <Text type="secondary">分析依据: {entity.rationale}</Text>
                          </div>
                        )}
                        {entity.key_interests && entity.key_interests.length > 0 && (
                          <div style={{ marginTop: 4 }}>
                            <Text type="secondary">核心利益: </Text>
                            {entity.key_interests.map((interest: string, idx: number) => (
                              <Tag key={idx} color="orange">{interest}</Tag>
                            ))}
                          </div>
                        )}
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        )}

        {/* 扩展查询展示 */}
        {expandedQueries.length > 0 && (
          <Card 
            title="智能查询扩展" 
            style={{ marginTop: 24 }}
            extra={<Tag color="purple">{expandedQueries.length} 个查询</Tag>}
          >
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              为收集全面情报自动生成的搜索查询
            </Text>
            <List
              dataSource={expandedQueries}
              renderItem={(query: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <div>
                        <Tag color={query.priority <= 2 ? 'red' : 'default'}>
                          优先级 {query.priority}
                        </Tag>
                        <Tag color="blue">{query.query_type}</Tag>
                        <Text strong style={{ marginLeft: 8 }}>{query.query}</Text>
                      </div>
                    }
                    description={
                      <div style={{ marginTop: 8 }}>
                        <Text type="secondary">{query.rationale}</Text>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        )}

        {/* 推演完成后展示因果图谱 */}
        {status === 'completed' && (
          <>
            {simulationResult && simulationResult.paths && simulationResult.paths.length > 0 ? (
              <Card 
                title="推演因果图谱" 
                style={{ marginTop: 24 }}
                extra={<Tag color="success">{simulationResult.paths.length} 条路径</Tag>}
              >
                <div style={{ height: '600px' }}>
                  <CausalGraph 
                    simulationData={{
                      paths: simulationResult.paths,
                      participatingAgents: simulationResult.participating_agents || []
                    }}
                  />
                </div>
              </Card>
            ) : (
              <Card 
                title="推演因果图谱" 
                style={{ marginTop: 24 }}
              >
                <Alert
                  message="暂无因果图谱数据"
                  description={simulationResult ? `推演结果中没有路径数据。paths: ${JSON.stringify(simulationResult.paths)}` : "推演结果为空"}
                  type="warning"
                  showIcon
                />
              </Card>
            )}
          </>
        )}

        {/* 情报收集阶段展示收集到的内容 */}
        {(currentStep === 0 || currentStep === 1) && collectedContents.length > 0 && (
          <Card 
            title="情报收集结果" 
            style={{ marginTop: 24 }}
            extra={<Text type="secondary">{collectedContents.length} 条内容</Text>}
          >
            <Collapse defaultActiveKey={['1']} ghost>
              <Panel header="查看收集到的文章" key="1">
                <List
                  dataSource={collectedContents}
                  renderItem={renderContentItem}
                  pagination={{
                    pageSize: 5,
                    size: 'small',
                    showSizeChanger: false
                  }}
                />
              </Panel>
            </Collapse>
          </Card>
        )}
      </Card>
    </div>
  )
}

export default Simulation
