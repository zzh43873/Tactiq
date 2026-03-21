import { useCallback, useState, useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  Panel,
  Position,
  Handle,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Card, Tag, Space, Typography, Select, Radio } from 'antd'
import { GlobalOutlined, ClockCircleOutlined, FireOutlined, TeamOutlined } from '@ant-design/icons'
import './style.css'

const { Title, Text } = Typography
const { Option } = Select

// 节点类型定义
interface CausalNodeData {
  label: string
  entity: string
  entityType: string
  action: string
  dimension: 'military' | 'economic' | 'diplomatic' | 'public_opinion'
  timeframe: 'short' | 'medium' | 'long'
  description: string
  impact: number
  location?: { lat: number; lng: number; name: string }
  [key: string]: unknown
}

// 自定义节点组件
const CausalNode = ({ data }: { data: CausalNodeData }) => {
  const dimensionColors = {
    military: '#ff4d4f',
    economic: '#52c41a',
    diplomatic: '#1890ff',
    public_opinion: '#faad14',
  }

  const timeframeLabels = {
    short: '短期',
    medium: '中期',
    long: '长期',
  }

  return (
    <Card
      size="small"
      className="causal-node"
      style={{
        borderLeft: `4px solid ${dimensionColors[data.dimension]}`,
        width: 220,
      }}
    >
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Space wrap>
          <Tag color={dimensionColors[data.dimension]}>
            {data.dimension === 'military' && <FireOutlined />}
            {data.dimension === 'economic' && <GlobalOutlined />}
            {data.dimension === 'diplomatic' && <TeamOutlined />}
            {data.dimension === 'public_opinion' && <ClockCircleOutlined />}
            <span style={{ marginLeft: 4 }}>
              {data.dimension === 'military' && '军事'}
              {data.dimension === 'economic' && '经济'}
              {data.dimension === 'diplomatic' && '外交'}
              {data.dimension === 'public_opinion' && '舆论'}
            </span>
          </Tag>
          <Tag>{timeframeLabels[data.timeframe]}</Tag>
        </Space>
        
        <Text strong style={{ fontSize: 14 }}>{data.entity}</Text>
        <Text style={{ fontSize: 12, color: '#666' }}>{data.action}</Text>
        
        {data.location && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            📍 {data.location.name}
          </Text>
        )}
      </Space>
    </Card>
  )
}

const nodeTypes = {
  causal: CausalNode,
}

interface CausalGraphProps {
  simulationData: {
    paths: Array<{
      id: string
      nodes: Array<{
        id: string
        entity: string
        entityType: string
        action: string
        dimension: string
        timeframe: string
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
    participatingAgents: string[]
  }
  onNodeClick?: (node: CausalNodeData) => void
}

export default function CausalGraph({ simulationData, onNodeClick }: CausalGraphProps) {
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('all')
  const [selectedDimension, setSelectedDimension] = useState<string>('all')
  const [selectedAgent, setSelectedAgent] = useState<string>('all')

  // 调试日志
  console.log('CausalGraph simulationData:', simulationData)
  console.log('CausalGraph paths:', simulationData?.paths)
  console.log('CausalGraph paths length:', simulationData?.paths?.length)

  // 转换数据为 React Flow 格式
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!simulationData?.paths?.length) {
      console.log('No paths available in simulationData')
      return { initialNodes: [], initialEdges: [] }
    }
    
    console.log('Processing paths:', simulationData.paths)

    const nodes: Node<CausalNodeData>[] = []
    const edges: Edge[] = []
    let yOffset = 0

    simulationData.paths.forEach((path, pathIndex) => {
      const pathNodes = path.nodes.map((node, nodeIndex) => ({
        id: `${path.id}-${node.id}`,
        type: 'causal',
        position: { 
          x: nodeIndex * 300, 
          y: pathIndex * 200 + yOffset 
        },
        data: {
          label: node.entity,
          entity: node.entity,
          entityType: node.entityType,
          action: node.action,
          dimension: node.dimension as CausalNodeData['dimension'],
          timeframe: node.timeframe as CausalNodeData['timeframe'],
          description: node.description,
          impact: node.impact,
          location: node.location,
        },
      }))

      const pathEdges = path.edges.map((edge, edgeIndex) => ({
        id: `e-${path.id}-${edgeIndex}`,
        source: `${path.id}-${edge.source}`,
        target: `${path.id}-${edge.target}`,
        label: edge.label,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#1890ff', strokeWidth: 2 },
      }))

      nodes.push(...pathNodes)
      edges.push(...pathEdges)
      yOffset += 50
    })

    return { initialNodes: nodes, initialEdges: edges }
  }, [simulationData])

  // 过滤节点
  const filteredNodes = useMemo(() => {
    return initialNodes.filter((node) => {
      const timeframeMatch = selectedTimeframe === 'all' || node.data.timeframe === selectedTimeframe
      const dimensionMatch = selectedDimension === 'all' || node.data.dimension === selectedDimension
      const agentMatch = selectedAgent === 'all' || node.data.entity === selectedAgent
      return timeframeMatch && dimensionMatch && agentMatch
    })
  }, [initialNodes, selectedTimeframe, selectedDimension, selectedAgent])

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map(n => n.id))
    return initialEdges.filter(edge => 
      nodeIds.has(edge.source) && nodeIds.has(edge.target)
    )
  }, [initialEdges, filteredNodes])

  const [nodes, setNodes, onNodesChange] = useNodesState(filteredNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(filteredEdges)

  // 更新节点和边当过滤条件变化
  useMemo(() => {
    setNodes(filteredNodes)
    setEdges(filteredEdges)
  }, [filteredNodes, filteredEdges, setNodes, setEdges])

  const onNodeClickHandler = useCallback((_: React.MouseEvent, node: Node<CausalNodeData>) => {
    onNodeClick?.(node.data)
  }, [onNodeClick])

  // 获取所有参与方
  const agents = useMemo(() => {
    const agentSet = new Set<string>()
    simulationData?.paths?.forEach(path => {
      path.nodes.forEach(node => agentSet.add(node.entity))
    })
    return Array.from(agentSet)
  }, [simulationData])

  return (
    <div className="causal-graph-container">
      <div className="causal-graph-filters">
        <Space wrap>
          <Radio.Group 
            value={selectedTimeframe} 
            onChange={(e) => setSelectedTimeframe(e.target.value)}
            buttonStyle="solid"
          >
            <Radio.Button value="all">全部时间</Radio.Button>
            <Radio.Button value="short">短期(1-3月)</Radio.Button>
            <Radio.Button value="medium">中期(6-12月)</Radio.Button>
            <Radio.Button value="long">长期(1-3年)</Radio.Button>
          </Radio.Group>

          <Select
            value={selectedDimension}
            onChange={setSelectedDimension}
            style={{ width: 120 }}
            placeholder="维度筛选"
          >
            <Option value="all">全部维度</Option>
            <Option value="military">军事</Option>
            <Option value="economic">经济</Option>
            <Option value="diplomatic">外交</Option>
            <Option value="public_opinion">舆论</Option>
          </Select>

          <Select
            value={selectedAgent}
            onChange={setSelectedAgent}
            style={{ width: 150 }}
            placeholder="行为体筛选"
          >
            <Option value="all">全部行为体</Option>
            {agents.map(agent => (
              <Option key={agent} value={agent}>{agent}</Option>
            ))}
          </Select>
        </Space>
      </div>

      <div className="causal-graph-flow">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClickHandler}
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
          />
          <Panel position="top-left">
            <Card size="small" title="图例">
              <Space direction="vertical" size="small">
                <div><span style={{ color: '#ff4d4f' }}>●</span> 军事</div>
                <div><span style={{ color: '#52c41a' }}>●</span> 经济</div>
                <div><span style={{ color: '#1890ff' }}>●</span> 外交</div>
                <div><span style={{ color: '#faad14' }}>●</span> 舆论</div>
              </Space>
            </Card>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  )
}
