import { useParams } from 'react-router-dom'
import { useState, useEffect, useMemo } from 'react'
import { Card, Typography, Button, Space, Tabs, Spin, Alert, Row, Col, Tag, Divider, List } from 'antd'
import { DownloadOutlined, ShareAltOutlined, GlobalOutlined, BranchesOutlined, WarningOutlined, CheckCircleOutlined, TeamOutlined } from '@ant-design/icons'
import CausalGraph from '../../components/CausalGraph'
import GeoMap from '../../components/GeoMap'
import EntityTopology from '../../components/EntityTopology'
import type { EntityNodeData, RelationshipEdgeData } from '../../components/EntityTopology'
import './style.css'

const { Title, Paragraph, Text } = Typography
const { TabPane } = Tabs

interface SimulationReport {
  id: string
  event_description: string
  participating_agents: string[]
  paths: Array<{
    id: string
    name: string
    assumption: string
    probability: number
    confidence: string
    nodes: Array<{
      id: string
      entity: string
      entityType: string
      action: string
      dimension: 'military' | 'economic' | 'diplomatic' | 'public_opinion'
      timeframe: 'short' | 'medium' | 'long'
      description: string
      impact: number
      location?: { lat: number; lng: number; name: string }
    }>
    edges: Array<{
      source: string
      target: string
      label?: string
      type?: string
    }>
  }>
  red_team_challenges: Array<{
    target_path: string
    challenge: string
    alternative_scenario?: string
    key_assumption_questioned: string
  }>
  synthesis: {
    key_uncertainties: Array<{
      factor: string
      impact: string
      possible_outcomes: string[]
    }>
    early_warning_indicators: Array<{
      indicator: string
      significance: string
      monitoring_source?: string
    }>
    overall_assessment: string
    strategic_implications: string[]
  }
  // 实体和关系数据
  identified_entities?: Array<{
    name: string
    entity_type: string
    role: string
    relevance_score: number
    key_interests: string[]
    stated_position?: string
  }>
  relationship_dynamics?: {
    active_conflicts: string[][]
    tensions: string[][]
    cooperation: string[][]
    key_relationships: Array<{
      // 新格式（LLM预识别）
      entity_a?: string
      entity_b?: string
      relationship?: string
      tension_level?: number
      description?: string
      source?: string
      target?: string
      type?: string
      dimension: string
      strength?: number
    }>
  }
}

function Report() {
  const { id } = useParams<{ id: string }>()
  const [report, setReport] = useState<SimulationReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)

  useEffect(() => {
    fetchReport()
  }, [id])

  const fetchReport = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/simulation/${id}`)
      if (!response.ok) {
        throw new Error('Failed to fetch report')
      }
      const data = await response.json()
      
      console.log('Report API response:', data)
      console.log('identified_entities:', data.identified_entities)
      console.log('relationship_dynamics:', data.relationship_dynamics)
      
      // 转换数据格式
      const formattedReport: SimulationReport = {
        id: data.id,
        event_description: data.event_description || '推演事件',
        participating_agents: data.participating_agents || [],
        paths: data.result?.paths?.map((path: any) => ({
          id: path.id,
          name: path.name,
          assumption: path.assumption,
          probability: path.probability,
          confidence: path.confidence,
          nodes: path.nodes || [],
          edges: path.edges || []
        })) || [],
        red_team_challenges: data.result?.red_team_challenges || [],
        synthesis: data.result?.synthesis || {
          key_uncertainties: [],
          early_warning_indicators: [],
          overall_assessment: '推演完成',
          strategic_implications: []
        },
        // 添加实体和关系数据
        identified_entities: data.identified_entities || [],
        relationship_dynamics: data.relationship_dynamics || null
      }
      
      console.log('Formatted report:', formattedReport)
      setReport(formattedReport)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  // 将所有路径的事件合并用于地图显示
  const mapEvents = report?.paths?.flatMap(path => 
    path.nodes
      .filter(node => node.location)
      .map(node => ({
        id: `${path.id}-${node.id}`,
        entity: node.entity,
        action: node.action,
        dimension: node.dimension,
        timeframe: node.timeframe,
        location: node.location!,
        impact: node.impact,
        description: node.description
      }))
  ) || []

  const handleNodeClick = (nodeData: any) => {
    // 查找对应的地图事件
    const eventId = mapEvents.find(e => e.entity === nodeData.entity)?.id
    if (eventId) {
      setSelectedEventId(eventId)
    }
  }

  const handleMapEventClick = (event: any) => {
    setSelectedEventId(event.id)
  }

  // 准备实体关系拓扑数据
  const topologyEntities: EntityNodeData[] = useMemo(() => {
    if (!report?.identified_entities) {
      console.log('No identified_entities in report')
      return []
    }
    console.log('Creating topologyEntities from:', report.identified_entities)
    return report.identified_entities.map((e, index) => ({
      id: `entity-${index}`,
      name: e.name,
      entityType: e.entity_type,
      role: e.role,
      relevanceScore: e.relevance_score,
      keyInterests: e.key_interests || [],
      statedPosition: e.stated_position || '',
      currentActions: (e as any).current_actions || [],
      nameEn: (e as any).name_en || '',
    }))
  }, [report?.identified_entities])

  // 准备关系数据
  const topologyRelationships: RelationshipEdgeData[] = useMemo(() => {
    if (!report?.relationship_dynamics) return []

    const dynamics = report.relationship_dynamics
    // 使用 Map 来合并同一对实体之间的多个维度关系
    const relationshipMap = new Map<string, RelationshipEdgeData>()

    // 从 key_relationships 构建关系（支持两种字段名格式）
    if (dynamics.key_relationships) {
      dynamics.key_relationships.forEach((rel, index) => {
        // 支持两种字段名：entity_a/entity_b (新格式) 或 source/target (旧格式)
        const sourceName = rel.entity_a || rel.source
        const targetName = rel.entity_b || rel.target

        if (!sourceName || !targetName) return

        const sourceId = topologyEntities.find(e => e.name === sourceName)?.id
        const targetId = topologyEntities.find(e => e.name === targetName)?.id

        if (sourceId && targetId) {
          // 确定关系类型和方向
          const relType = rel.relationship || rel.type || '未知关系'
          const isConflict = relType.includes('冲突') ||
                            relType.includes('对抗') ||
                            relType.includes('战争') ||
                            (rel.tension_level !== undefined && rel.tension_level > 0.7)

          // 创建唯一键（确保 A-B 和 B-A 被视为同一对）
          const edgeKey = [sourceId, targetId].sort().join('-')

          const relationshipType = {
            type: relType,
            label: relType,
            dimension: rel.dimension || 'political',
            strength: rel.tension_level || rel.strength || 0.5,
            direction: isConflict ? 'conflict' : 'bidirectional' as const,
            description: rel.description || '',
          }

          if (relationshipMap.has(edgeKey)) {
            // 已存在该实体对的关系，添加新的维度关系
            const existing = relationshipMap.get(edgeKey)!
            existing.relationships.push(relationshipType)
          } else {
            // 创建新的关系边
            relationshipMap.set(edgeKey, {
              id: `rel-${edgeKey}`,
              source: sourceId,
              target: targetId,
              relationships: [relationshipType],
            })
          }
        }
      })
    }

    // 从 active_conflicts 构建冲突关系
    dynamics.active_conflicts?.forEach((pair, index) => {
      const [sourceName, targetName] = pair
      const sourceId = topologyEntities.find(e => e.name === sourceName)?.id
      const targetId = topologyEntities.find(e => e.name === targetName)?.id

      if (sourceId && targetId) {
        const edgeKey = [sourceId, targetId].sort().join('-')
        const conflictRel = {
          type: '军事冲突',
          label: '军事冲突',
          dimension: 'security',
          strength: 0.9,
          direction: 'conflict' as const,
        }

        if (relationshipMap.has(edgeKey)) {
          const existing = relationshipMap.get(edgeKey)!
          // 检查是否已存在 security 维度的关系
          const hasSecurity = existing.relationships.some(r => r.dimension === 'security')
          if (!hasSecurity) {
            existing.relationships.push(conflictRel)
          }
        } else {
          relationshipMap.set(edgeKey, {
            id: `conflict-${edgeKey}`,
            source: sourceId,
            target: targetId,
            relationships: [conflictRel],
          })
        }
      }
    })

    // 从 cooperation 构建合作关系
    dynamics.cooperation?.forEach((pair, index) => {
      const [sourceName, targetName] = pair
      const sourceId = topologyEntities.find(e => e.name === sourceName)?.id
      const targetId = topologyEntities.find(e => e.name === targetName)?.id

      if (sourceId && targetId) {
        const edgeKey = [sourceId, targetId].sort().join('-')
        const coopRel = {
          type: '合作同盟',
          label: '合作同盟',
          dimension: 'political',
          strength: 0.7,
          direction: 'bidirectional' as const,
        }

        if (relationshipMap.has(edgeKey)) {
          const existing = relationshipMap.get(edgeKey)!
          // 检查是否已存在 political 维度的关系
          const hasPolitical = existing.relationships.some(r => r.dimension === 'political')
          if (!hasPolitical) {
            existing.relationships.push(coopRel)
          }
        } else {
          relationshipMap.set(edgeKey, {
            id: `coop-${edgeKey}`,
            source: sourceId,
            target: targetId,
            relationships: [coopRel],
          })
        }
      }
    })

    const result = Array.from(relationshipMap.values())
    console.log('Created topologyRelationships:', result)
    return result
  }, [report?.relationship_dynamics, topologyEntities])

  if (loading) {
    return (
      <div className="report-container">
        <Spin size="large" tip="加载报告...">
          <div style={{ minHeight: 400 }} />
        </Spin>
      </div>
    )
  }

  if (error) {
    return (
      <div className="report-container">
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
        />
      </div>
    )
  }

  if (!report) {
    return (
      <div className="report-container">
        <Alert
          message="报告不存在"
          description="未找到该推演报告"
          type="warning"
          showIcon
        />
      </div>
    )
  }

  return (
    <div className="report-container">
      <Card className="report-header-card">
        <div className="report-header">
          <div>
            <Title level={3}>推演报告</Title>
            <Paragraph type="secondary">{report.event_description}</Paragraph>
          </div>
          <Space>
            <Button icon={<DownloadOutlined />}>导出PDF</Button>
            <Button icon={<ShareAltOutlined />}>分享</Button>
          </Space>
        </div>
        
        <Space wrap style={{ marginTop: 16 }}>
          <Tag icon={<GlobalOutlined />} color="blue">
            参与方: {report.participating_agents.length} 个
          </Tag>
          <Tag icon={<BranchesOutlined />} color="green">
            推演路径: {report.paths.length} 条
          </Tag>
          <Tag icon={<WarningOutlined />} color="orange">
            红队挑战: {report.red_team_challenges.length} 条
          </Tag>
        </Space>
      </Card>

      <Tabs defaultActiveKey="causal" className="report-tabs">
        <TabPane
          tab={<span><BranchesOutlined /> 因果图谱</span>}
          key="causal"
        >
          <Row gutter={16}>
            <Col span={16}>
              <Card title="推演因果网络" className="graph-card">
                <CausalGraph
                  simulationData={{
                    paths: report.paths,
                    participatingAgents: report.participating_agents
                  }}
                  onNodeClick={handleNodeClick}
                />
              </Card>
            </Col>
            <Col span={8}>
              <GeoMap
                events={mapEvents}
                selectedEventId={selectedEventId || undefined}
                onEventClick={handleMapEventClick}
              />
            </Col>
          </Row>
        </TabPane>

        <TabPane
          tab={<span><TeamOutlined /> 实体关系拓扑</span>}
          key="topology"
        >
          <Row gutter={16}>
            <Col span={24}>
              <EntityTopology
                entities={topologyEntities}
                relationships={topologyRelationships}
                onEntityClick={(entity) => {
                  console.log('Clicked entity:', entity)
                }}
              />
            </Col>
          </Row>
        </TabPane>

        <TabPane
          tab={<span><WarningOutlined /> 红队挑战</span>}
          key="challenges"
        >
          <Card title="红队挑战与质疑">
            <List
              dataSource={report.red_team_challenges}
              renderItem={(challenge, index) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<WarningOutlined style={{ color: '#faad14', fontSize: 24 }} />}
                    title={`挑战 ${index + 1}: ${challenge.key_assumption_questioned}`}
                    description={
                      <div>
                        <Paragraph>{challenge.challenge}</Paragraph>
                        {challenge.alternative_scenario && (
                          <Paragraph type="secondary">
                            <strong>替代情景:</strong> {challenge.alternative_scenario}
                          </Paragraph>
                        )}
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </TabPane>

        <TabPane 
          tab={<span><CheckCircleOutlined /> 综合评估</span>} 
          key="synthesis"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Card title="关键不确定性">
                <List
                  dataSource={report.synthesis.key_uncertainties}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        title={item.factor}
                        description={
                          <div>
                            <Text>影响: {item.impact}</Text>
                            <div style={{ marginTop: 8 }}>
                              {item.possible_outcomes.map((outcome, idx) => (
                                <Tag key={idx} style={{ margin: 2 }}>{outcome}</Tag>
                              ))}
                            </div>
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="早期预警指标">
                <List
                  dataSource={report.synthesis.early_warning_indicators}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        title={item.indicator}
                        description={
                          <div>
                            <Text>重要性: {item.significance}</Text>
                            {item.monitoring_source && (
                              <div><Text type="secondary">监测源: {item.monitoring_source}</Text></div>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>

          <Divider />

          <Card title="总体评估">
            <Paragraph>{report.synthesis.overall_assessment}</Paragraph>
          </Card>

          {report.synthesis.strategic_implications.length > 0 && (
            <Card title="战略启示" style={{ marginTop: 16 }}>
              <List
                dataSource={report.synthesis.strategic_implications}
                renderItem={(item) => (
                  <List.Item>
                    <Text>• {item}</Text>
                  </List.Item>
                )}
              />
            </Card>
          )}
        </TabPane>
      </Tabs>
    </div>
  )
}

export default Report
