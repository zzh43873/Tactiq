                                      import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Input, Button, Typography, Space, Alert, Table, Tag, Badge, Modal, Divider, Tabs } from 'antd'
import { PlayCircleOutlined, HistoryOutlined, ClockCircleOutlined, FileTextOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import CausalGraph from '../../components/CausalGraph'
import './style.css'

const { Title, Paragraph } = Typography
const { TextArea } = Input

interface HistoryItem {
  id: string
  event_description: string
  pre_identified_entities: any[]
  pre_identified_relationships?: any[]
  identified_entities: any[]
  created_at: string
  updated_at: string
  hit_count: number
  article_count: number
  has_simulation?: boolean
  simulation_result?: {
    paths?: any[]
    participating_agents?: string[]
  }
}

function Home() {
  const navigate = useNavigate()
  const [eventDescription, setEventDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [reportModalVisible, setReportModalVisible] = useState(false)
  const [selectedReport, setSelectedReport] = useState<HistoryItem | null>(null)

  // 加载历史记录
  useEffect(() => {
    fetchHistory()
  }, [])

  const fetchHistory = async () => {
    setHistoryLoading(true)
    try {
      const response = await fetch('/api/v1/intelligence/history?limit=10')
      if (response.ok) {
        const data = await response.json()
        console.log('History data:', data)
        setHistory(data.items || [])
      } else {
        console.error('Failed to fetch history:', response.status, await response.text())
      }
    } catch (error) {
      console.error('Failed to fetch history:', error)
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleStartSimulation = async () => {
    if (!eventDescription.trim()) {
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/v1/simulation/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_description: eventDescription,
          config: { max_rounds: 5 }
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        navigate(`/simulation/${data.id}`)
      }
    } catch (error) {
      console.error('Failed to start simulation:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUseHistory = (description: string) => {
    setEventDescription(description)
  }

  const handleViewReport = (record: HistoryItem) => {
    // 从缓存中获取推演结果
    const simulationResult = (record as any).simulation_result
    if (simulationResult) {
      setSelectedReport({
        ...record,
        simulation_result: simulationResult
      })
    } else {
      setSelectedReport(record)
    }
    setReportModalVisible(true)
  }

  const handleCloseReport = () => {
    setReportModalVisible(false)
    setSelectedReport(null)
  }

  // 生成关系图配置
  const getGraphOption = (entities: any[], relationships: any[]) => {
    if (!entities || entities.length === 0) {
      return { nodes: [], links: [] }
    }

    const nodes = entities.map((entity: any, index: number) => ({
      id: entity.name || `entity_${index}`,
      name: entity.name || 'Unknown',
      symbolSize: Math.max(30, (entity.relevance || entity.relevance_score || 0.5) * 60),
      value: entity.relevance || entity.relevance_score || 0.5,
      category: entity.entity_type || 'unknown',
      itemStyle: {
        color: entity.entity_type === 'country' ? '#5470c6' : 
               entity.entity_type === 'organization' ? '#91cc75' :
               entity.entity_type === 'non_state_actor' ? '#ee6666' : '#fac858'
      },
      label: {
        show: true,
        formatter: '{b}',
        fontSize: 12
      }
    }))

    const links = (relationships || []).map((rel: any) => ({
      source: rel.entity_a,
      target: rel.entity_b,
      value: rel.relationship,
      lineStyle: {
        color: rel.tension_level > 0.5 ? '#ff4d4f' : '#52c41a',
        width: 2
      }
    }))

    return {
      title: {
        text: '实体关系网络',
        left: 'center',
        textStyle: { color: '#333' }
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            return `<strong>${params.data.name}</strong><br/>类型: ${params.data.category}`
          }
          return `${params.data.source} → ${params.data.target}`
        }
      },
      series: [{
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: links,
        roam: true,
        draggable: true,
        force: {
          repulsion: 300,
          gravity: 0.1,
          edgeLength: [100, 200]
        },
        emphasis: {
          focus: 'adjacency'
        }
      }]
    }
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const isFresh = (updatedAt: string) => {
    if (!updatedAt) return false
    const updated = new Date(updatedAt)
    const now = new Date()
    const hoursDiff = (now.getTime() - updated.getTime()) / (1000 * 60 * 60)
    return hoursDiff < 24
  }

  const historyColumns = [
    {
      title: '推演命题',
      dataIndex: 'event_description',
      key: 'event_description',
      ellipsis: true,
      render: (text: string) => (
        <span style={{ fontWeight: 500 }}>{text}</span>
      )
    },
    {
      title: '实体数量',
      dataIndex: 'pre_identified_entities',
      key: 'entity_count',
      width: 100,
      align: 'center' as const,
      render: (entities: any[]) => (
        <Tag color="blue">{entities?.length || 0} 个</Tag>
      )
    },
    {
      title: '文章数量',
      key: 'article_count',
      width: 100,
      align: 'center' as const,
      render: (_: any, record: HistoryItem) => {
        // 从 collected_articles 或 article_count 获取数量
        const articleCount = record.article_count || 
          (record as any).collected_articles?.length || 
          (record as any).articles?.length || 
          0
        return <Tag color="green">{articleCount} 篇</Tag>
      }
    },
    {
      title: '推演状态',
      key: 'simulation_status',
      width: 120,
      align: 'center' as const,
      render: (_: any, record: HistoryItem) => {
        const hasSimulation = (record as any).has_simulation
        if (hasSimulation) {
          return <Badge status="success" text="已完成" />
        } else {
          return <Badge status="default" text="未推演" />
        }
      }
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 150,
      render: (text: string) => (
        <span style={{ color: '#666' }}>
          <ClockCircleOutlined style={{ marginRight: 4 }} />
          {formatDate(text)}
        </span>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      align: 'center' as const,
      render: (_: any, record: HistoryItem) => (
        <Space>
          <Button 
            type="primary" 
            size="small"
            onClick={() => handleViewReport(record)}
          >
            查看报告
          </Button>
          <Button 
            type="link" 
            size="small"
            onClick={() => handleUseHistory(record.event_description)}
          >
            使用
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div className="home-container">
      <Card className="welcome-card">
        <Title level={2}>地缘政治推演系统</Title>
        <Paragraph type="secondary">
          基于多Agent技术的战略推演平台，帮助您理解复杂国际事件的连锁反应
        </Paragraph>
      </Card>

      <Card className="input-card" title="输入推演命题">
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Alert
            message="使用说明"
            description="输入一个地缘政治事件命题，系统将自动收集情报、识别相关方，并进行多维度推演。"
            type="info"
            showIcon
          />
          
          <TextArea
            placeholder="例如：美国出兵伊朗的推演"
            value={eventDescription}
            onChange={(e) => setEventDescription(e.target.value)}
            rows={4}
            maxLength={500}
            showCount
          />

          <Button
            type="primary"
            size="large"
            icon={<PlayCircleOutlined />}
            onClick={handleStartSimulation}
            loading={loading}
            disabled={!eventDescription.trim()}
            block
          >
            开始推演
          </Button>
        </Space>
      </Card>

      <Card className="examples-card" title="示例命题">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button 
            type="link" 
            onClick={() => setEventDescription('美国出兵伊朗的推演')}
          >
            美国出兵伊朗的推演
          </Button>
          <Button 
            type="link" 
            onClick={() => setEventDescription('台海局势升级的影响')}
          >
            台海局势升级的影响
          </Button>
          <Button 
            type="link" 
            onClick={() => setEventDescription('俄罗斯与北约冲突推演')}
          >
            俄罗斯与北约冲突推演
          </Button>
        </Space>
      </Card>

      <Card 
        className="history-card" 
        title={
          <span>
            <HistoryOutlined style={{ marginRight: 8 }} />
            历史记录
          </span>
        }
        loading={historyLoading}
      >
        <Table
          dataSource={history}
          columns={historyColumns}
          rowKey="id"
          pagination={false}
          size="small"
          locale={{ emptyText: '暂无历史记录，请开始一个新的推演' }}
        />
        <Paragraph type="secondary" style={{ marginTop: 12, fontSize: 12 }}>
          提示："已完成"表示推演成功并生成了因果图谱；"未推演"表示仅完成了情报收集，未进行推演分析
        </Paragraph>
      </Card>

      {/* 报告查看弹窗 */}
      <Modal
        title={
          <span>
            <FileTextOutlined style={{ marginRight: 8 }} />
            推演报告
          </span>
        }
        open={reportModalVisible}
        onCancel={handleCloseReport}
        width={1400}
        footer={[
          <Button key="close" onClick={handleCloseReport}>
            关闭
          </Button>
        ]}
      >
        {selectedReport && (
          <div>
            {/* 推演描述 */}
            <Paragraph type="secondary" style={{ marginBottom: 16 }}>
              {selectedReport.event_description}
            </Paragraph>
            
            {/* 因果图谱 */}
            {(selectedReport.simulation_result?.paths && selectedReport.simulation_result.paths.length > 0) ? (
              <div style={{ height: '600px', marginBottom: 24 }}>
                <Title level={4}>推演因果图谱</Title>
                <CausalGraph 
                  simulationData={{
                    paths: selectedReport.simulation_result.paths,
                    participatingAgents: selectedReport.simulation_result.participating_agents || []
                  }}
                />
              </div>
            ) : (
              <Alert 
                message="暂无因果图谱" 
                description={selectedReport.has_simulation ? "该推演结果中没有因果路径数据" : "该推演尚未进行推演分析，仅完成了情报收集"}
                type="info" 
                showIcon
                style={{ marginBottom: 24 }}
              />
            )}
            
            <Divider />
            
            {/* 实体信息 */}
            <Title level={4}>识别的实体</Title>
            <div style={{ display: 'flex', gap: '24px', height: 'calc(100vh - 500px)', minHeight: '500px' }}>
              {/* 左侧：实体列表 */}
              <div style={{ flex: '0 0 350px', height: '100%', overflowY: 'auto' }}>
                {(selectedReport.pre_identified_entities || []).map((entity: any, index: number) => (
                  <Card 
                    key={index} 
                    size="small" 
                    style={{ marginBottom: 12 }}
                    title={
                      <Space>
                        <Tag color={
                          entity.entity_type === 'country' ? 'blue' : 
                          entity.entity_type === 'organization' ? 'green' : 'orange'
                        }>
                          {entity.entity_type}
                        </Tag>
                        <span style={{ fontWeight: 'bold' }}>{entity.name}</span>
                      </Space>
                    }
                  >
                    <p><strong>角色:</strong> {entity.role}</p>
                    <p><strong>相关性:</strong> {((entity.relevance || 0) * 100).toFixed(0)}%</p>
                    {entity.rationale && (
                      <p><strong>分析依据:</strong> {entity.rationale}</p>
                    )}
                    {entity.key_interests && entity.key_interests.length > 0 && (
                      <div>
                        <strong>核心利益:</strong>
                        <div style={{ marginTop: 4 }}>
                          {entity.key_interests.map((interest: string, idx: number) => (
                            <Tag key={idx} style={{ margin: 2 }}>{interest}</Tag>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>

              {/* 右侧：关系拓扑图 */}
              <div style={{ flex: 1, height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Title level={5}>实体关系拓扑</Title>
                <div style={{ flex: 1, minHeight: 0 }}>
                  <ReactECharts
                    option={getGraphOption(
                      selectedReport.pre_identified_entities,
                      selectedReport.pre_identified_relationships || []
                    )}
                    style={{ height: '100%', width: '100%' }}
                    opts={{ renderer: 'canvas' }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default Home
