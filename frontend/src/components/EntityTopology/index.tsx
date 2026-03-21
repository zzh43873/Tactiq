import { useState, useMemo, useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  Position,
  Handle,
  EdgeClickHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Card, Tag, Space, Typography, Checkbox, Row, Col, Tooltip, Badge, Drawer, List, Divider } from 'antd'
import {
  BankOutlined,
  SecurityScanOutlined,
  DollarOutlined,
  TeamOutlined,
  FlagOutlined,
  GlobalOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import './style.css'

const { Text, Title, Paragraph } = Typography

// 关系维度定义
export interface RelationshipDimension {
  key: string
  label: string
  color: string
  icon: React.ReactNode
  description: string
}

export const RELATIONSHIP_DIMENSIONS: RelationshipDimension[] = [
  {
    key: 'political',
    label: '政治外交',
    color: '#1890ff',
    icon: <BankOutlined />,
    description: '政治与外交关系',
  },
  {
    key: 'security',
    label: '安全军事',
    color: '#ff4d4f',
    icon: <SecurityScanOutlined />,
    description: '安全与军事合作',
  },
  {
    key: 'economic',
    label: '经济贸易',
    color: '#52c41a',
    icon: <DollarOutlined />,
    description: '经济与贸易联系',
  },
  {
    key: 'social',
    label: '社会文化',
    color: '#faad14',
    icon: <TeamOutlined />,
    description: '社会文化纽带',
  },
  {
    key: 'ideological',
    label: '意识形态',
    color: '#722ed1',
    icon: <FlagOutlined />,
    description: '意识形态与价值观',
  },
  {
    key: 'geostrategic',
    label: '地缘战略',
    color: '#13c2c2',
    icon: <GlobalOutlined />,
    description: '地缘战略互动',
  },
]

// 关系类型定义
export interface RelationshipType {
  type: string
  label: string
  dimension: string
  strength: number // 0-1
  direction: 'unidirectional' | 'bidirectional' | 'conflict'
  description?: string
  analysisBasis?: string
}

// 实体节点数据
export interface EntityNodeData {
  id: string
  name: string
  entityType: string
  role: string
  relevanceScore: number
  keyInterests: string[]
  statedPosition: string
  currentActions?: string[]
  nameEn?: string
  analysisBasis?: string
  [key: string]: unknown
}

// 关系边数据
export interface RelationshipEdgeData {
  id: string
  source: string
  target: string
  relationships: RelationshipType[]
}

// 组件属性
interface EntityTopologyProps {
  entities: EntityNodeData[]
  relationships: RelationshipEdgeData[]
  onEntityClick?: (entity: EntityNodeData) => void
}

// 自定义实体节点组件
const EntityNode = ({ data }: { data: EntityNodeData }) => {
  const getEntityTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      country: '#1890ff',
      organization: '#52c41a',
      non_state_armed: '#ff4d4f',
      international_org: '#faad14',
    }
    return colors[type] || '#999'
  }

  const getRoleLabel = (role: string) => {
    const labels: Record<string, string> = {
      initiator: '发起方',
      target: '目标方',
      ally: '盟友',
      adversary: '对手',
      mediator: '调解方',
      stakeholder: '利益相关方',
    }
    return labels[role] || role
  }

  return (
    <Card
      size="small"
      className="topology-entity-node"
      style={{
        borderTop: `4px solid ${getEntityTypeColor(data.entityType)}`,
        width: 180,
      }}
    >
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />

      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <div className="entity-header">
          <Text strong className="entity-name">{data.name}</Text>
          <Badge
            count={getRoleLabel(data.role)}
            style={{
              backgroundColor: getEntityTypeColor(data.entityType),
              fontSize: 10,
            }}
          />
        </div>

        <div className="entity-meta">
          <Tooltip title={`相关度: ${(data.relevanceScore * 100).toFixed(0)}%`}>
            <div className="relevance-bar">
              <div
                className="relevance-fill"
                style={{
                  width: `${data.relevanceScore * 100}%`,
                  backgroundColor: getEntityTypeColor(data.entityType),
                }}
              />
            </div>
          </Tooltip>
        </div>

        {data.keyInterests.length > 0 && (
          <div className="entity-interests">
            {data.keyInterests.slice(0, 2).map((interest, idx) => (
              <Tag key={idx} style={{ fontSize: 10, margin: 2 }}>
                {interest}
              </Tag>
            ))}
            {data.keyInterests.length > 2 && (
              <Tag style={{ fontSize: 10, margin: 2 }}>
                +{data.keyInterests.length - 2}
              </Tag>
            )}
          </div>
        )}
      </Space>
    </Card>
  )
}

const nodeTypes = {
  entity: EntityNode,
}

export default function EntityTopology({
  entities,
  relationships,
  onEntityClick,
}: EntityTopologyProps) {
  console.log('EntityTopology received entities:', entities.length, entities)
  console.log('EntityTopology received relationships:', relationships.length, relationships)

  // 可见维度状态
  const [visibleDimensions, setVisibleDimensions] = useState<string[]>(
    RELATIONSHIP_DIMENSIONS.map(d => d.key)
  )

  // 详情面板状态
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false)
  const [selectedNode, setSelectedNode] = useState<EntityNodeData | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<{ edge: RelationshipEdgeData; relationship: RelationshipType } | null>(null)

  // 计算节点位置（使用力导向布局的简化版本）
  const calculateNodePositions = useCallback((entities: EntityNodeData[]) => {
    const positions: Record<string, { x: number; y: number }> = {}
    const centerX = 400
    const centerY = 300
    const radius = 250

    entities.forEach((entity, index) => {
      const angle = (2 * Math.PI * index) / entities.length - Math.PI / 2
      positions[entity.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      }
    })

    return positions
  }, [])

  // 根据可见维度过滤关系
  const filteredRelationships = useMemo(() => {
    return relationships.map(edge => ({
      ...edge,
      relationships: edge.relationships.filter(
        r => visibleDimensions.includes(r.dimension)
      ),
    })).filter(edge => edge.relationships.length > 0)
  }, [relationships, visibleDimensions])

  // 生成 React Flow 节点
  const nodePositions = useMemo(() => calculateNodePositions(entities), [entities, calculateNodePositions])

  const initialNodes: Node<EntityNodeData>[] = useMemo(() => {
    return entities.map(entity => ({
      id: entity.id,
      type: 'entity',
      position: nodePositions[entity.id] || { x: 0, y: 0 },
      data: entity,
    }))
  }, [entities, nodePositions])

  // 生成 React Flow 边（每个维度一条边）
  const initialEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = []
    console.log('Generating edges from filteredRelationships:', filteredRelationships)

    filteredRelationships.forEach(edgeData => {
      const totalRels = edgeData.relationships.length
      console.log(`Processing edgeData ${edgeData.id} with ${totalRels} relationships:`, edgeData.relationships)

      edgeData.relationships.forEach((rel, idx) => {
        const dimension = RELATIONSHIP_DIMENSIONS.find(d => d.key === rel.dimension)
        if (!dimension) {
          console.warn(`Unknown dimension: ${rel.dimension}`)
          return
        }

        const edgeId = `${edgeData.id}-${rel.dimension}-${idx}`
        console.log(`Creating edge ${edgeId}: ${edgeData.source} -> ${edgeData.target}, dimension: ${rel.dimension}`)

        // 根据关系类型设置线条样式
        let edgeStyle: React.CSSProperties = {
          stroke: dimension.color,
          strokeWidth: 2 + rel.strength * 3,
        }

        // 冲突关系使用虚线
        if (rel.direction === 'conflict') {
          edgeStyle.strokeDasharray = '5,5'
        }

        // 单向关系使用有向箭头
        const markerEnd = rel.direction === 'unidirectional'
          ? { type: 'arrowclosed' as const, color: dimension.color }
          : undefined

        edges.push({
          id: edgeId,
          source: edgeData.source,
          target: edgeData.target,
          label: rel.label,
          type: 'smoothstep',
          style: edgeStyle,
          markerEnd,
          animated: rel.strength > 0.7,
          data: { dimension: rel.dimension, relationship: rel },
        })
      })
    })

    console.log('Generated edges:', edges)
    return edges
  }, [filteredRelationships])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // 更新节点和边
  useMemo(() => {
    setNodes(initialNodes)
    setEdges(initialEdges)
  }, [initialNodes, initialEdges, setNodes, setEdges])

  // 处理维度切换
  const handleDimensionToggle = (dimensionKey: string, checked: boolean) => {
    if (checked) {
      setVisibleDimensions(prev => [...prev, dimensionKey])
    } else {
      setVisibleDimensions(prev => prev.filter(d => d !== dimensionKey))
    }
  }

  // 处理节点点击
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<EntityNodeData>) => {
      setSelectedNode(node.data)
      setSelectedEdge(null)
      setDetailDrawerVisible(true)
      onEntityClick?.(node.data)
    },
    [onEntityClick]
  )

  // 处理边点击
  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      const edgeData = relationships.find(r => r.id === edge.id || edge.id.startsWith(r.id))
      if (edgeData && edge.data?.relationship) {
        setSelectedEdge({ edge: edgeData, relationship: edge.data.relationship })
        setSelectedNode(null)
        setDetailDrawerVisible(true)
      }
    },
    [relationships]
  )

  // 关闭详情面板
  const handleCloseDrawer = () => {
    setDetailDrawerVisible(false)
    setSelectedNode(null)
    setSelectedEdge(null)
  }

  return (
    <Card
      className="entity-topology-container"
      title="实体关系拓扑"
      extra={
        <Space>
          <Text type="secondary">{entities.length} 个实体</Text>
          <Text type="secondary">{filteredRelationships.length} 组关系</Text>
        </Space>
      }
    >
      {/* 维度过滤器 */}
      <div className="topology-filters">
        <Text strong style={{ marginRight: 12 }}>关系维度:</Text>
        <Row gutter={[8, 8]}>
          {RELATIONSHIP_DIMENSIONS.map(dimension => (
            <Col key={dimension.key}>
              <Tooltip title={dimension.description}>
                <Checkbox
                  checked={visibleDimensions.includes(dimension.key)}
                  onChange={e => handleDimensionToggle(dimension.key, e.target.checked)}
                >
                  <Tag
                    color={dimension.color}
                    icon={dimension.icon}
                    style={{ margin: 0 }}
                  >
                    {dimension.label}
                  </Tag>
                </Checkbox>
              </Tooltip>
            </Col>
          ))}
        </Row>
      </div>

      {/* 图例 */}
      <div className="topology-legend">
        <Space size="large">
          <div className="legend-item">
            <div className="legend-line solid" />
            <Text type="secondary">合作/同盟</Text>
          </div>
          <div className="legend-item">
            <div className="legend-line dashed" />
            <Text type="secondary">冲突/对抗</Text>
          </div>
          <div className="legend-item">
            <div className="legend-line arrow" />
            <Text type="secondary">单向影响</Text>
          </div>
          <div className="legend-item">
            <div className="legend-line animated" />
            <Text type="secondary">高强度</Text>
          </div>
        </Space>
      </div>

      {/* 关系图 */}
      <div className="topology-graph">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-right"
        >
          <Background color="#e8e8e8" gap={16} />
          <Controls />
          <MiniMap
            nodeStrokeWidth={3}
            zoomable
            pannable
            nodeColor={(node) => {
              const colors: Record<string, string> = {
                country: '#1890ff',
                organization: '#52c41a',
                non_state_armed: '#ff4d4f',
                international_org: '#faad14',
              }
              const entityType = (node.data as EntityNodeData | undefined)?.entityType
              return colors[entityType || ''] || '#999'
            }}
          />
        </ReactFlow>
      </div>

      {/* 详情面板 */}
      <Drawer
        title={
          selectedNode ? (
            <Space>
              <InfoCircleOutlined />
              <span>实体详情: {selectedNode.name}</span>
            </Space>
          ) : selectedEdge ? (
            <Space>
              <InfoCircleOutlined />
              <span>关系详情</span>
            </Space>
          ) : (
            '详情'
          )
        }
        placement="right"
        onClose={handleCloseDrawer}
        open={detailDrawerVisible}
        width={400}
      >
        {selectedNode && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {/* 基本信息 */}
            <div>
              <Title level={5}>基本信息</Title>
              <Paragraph>
                <Text strong>名称: </Text>
                <Text>{selectedNode.name}</Text>
                {selectedNode.nameEn && (
                  <Text type="secondary"> ({selectedNode.nameEn})</Text>
                )}
              </Paragraph>
              <Paragraph>
                <Text strong>类型: </Text>
                <Tag color={RELATIONSHIP_DIMENSIONS.find(d => d.key === selectedNode.entityType)?.color || '#999'}>
                  {selectedNode.entityType}
                </Tag>
              </Paragraph>
              <Paragraph>
                <Text strong>角色: </Text>
                <Text>{selectedNode.role}</Text>
              </Paragraph>
              <Paragraph>
                <Text strong>相关度: </Text>
                <Text>{(selectedNode.relevanceScore * 100).toFixed(0)}%</Text>
              </Paragraph>
            </div>

            <Divider />

            {/* 核心利益 */}
            {selectedNode.keyInterests && selectedNode.keyInterests.length > 0 && (
              <div>
                <Title level={5}>核心利益</Title>
                <List
                  size="small"
                  dataSource={selectedNode.keyInterests}
                  renderItem={(interest) => (
                    <List.Item>
                      <Tag color="orange">{interest}</Tag>
                    </List.Item>
                  )}
                />
              </div>
            )}

            {/* 当前行动 */}
            {selectedNode.currentActions && selectedNode.currentActions.length > 0 && (
              <>
                <Divider />
                <div>
                  <Title level={5}>当前行动</Title>
                  <List
                    size="small"
                    dataSource={selectedNode.currentActions}
                    renderItem={(action) => (
                      <List.Item>
                        <Text>{action}</Text>
                      </List.Item>
                    )}
                  />
                </div>
              </>
            )}

            {/* 公开立场 */}
            {selectedNode.statedPosition && (
              <>
                <Divider />
                <div>
                  <Title level={5}>公开立场</Title>
                  <Paragraph>
                    <Text>{selectedNode.statedPosition}</Text>
                  </Paragraph>
                </div>
              </>
            )}

            {/* 分析依据 */}
            {selectedNode.analysisBasis && (
              <>
                <Divider />
                <div>
                  <Title level={5}>分析依据</Title>
                  <Paragraph>
                    <Text type="secondary">{selectedNode.analysisBasis}</Text>
                  </Paragraph>
                </div>
              </>
            )}
          </Space>
        )}

        {selectedEdge && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {/* 关系基本信息 */}
            <div>
              <Title level={5}>关系信息</Title>
              <Paragraph>
                <Text strong>关系类型: </Text>
                <Text>{selectedEdge.relationship.label}</Text>
              </Paragraph>
              <Paragraph>
                <Text strong>维度: </Text>
                <Tag
                  color={RELATIONSHIP_DIMENSIONS.find(d => d.key === selectedEdge.relationship.dimension)?.color}
                  icon={RELATIONSHIP_DIMENSIONS.find(d => d.key === selectedEdge.relationship.dimension)?.icon}
                >
                  {RELATIONSHIP_DIMENSIONS.find(d => d.key === selectedEdge.relationship.dimension)?.label}
                </Tag>
              </Paragraph>
              <Paragraph>
                <Text strong>强度: </Text>
                <Text>{(selectedEdge.relationship.strength * 100).toFixed(0)}%</Text>
              </Paragraph>
              <Paragraph>
                <Text strong>方向: </Text>
                <Tag>
                  {selectedEdge.relationship.direction === 'conflict' ? '冲突/对抗' :
                   selectedEdge.relationship.direction === 'unidirectional' ? '单向影响' : '双向互动'}
                </Tag>
              </Paragraph>
            </div>

            {/* 关系描述 */}
            {selectedEdge.relationship.description && (
              <>
                <Divider />
                <div>
                  <Title level={5}>关系描述</Title>
                  <Paragraph>
                    <Text>{selectedEdge.relationship.description}</Text>
                  </Paragraph>
                </div>
              </>
            )}

            {/* 分析依据 */}
            {selectedEdge.relationship.analysisBasis && (
              <>
                <Divider />
                <div>
                  <Title level={5}>分析依据</Title>
                  <Paragraph>
                    <Text type="secondary">{selectedEdge.relationship.analysisBasis}</Text>
                  </Paragraph>
                </div>
              </>
            )}
          </Space>
        )}
      </Drawer>
    </Card>
  )
}
