/**
 * Simulation Workflow Visualizer
 * 
 * Displays the LangGraph state machine with real-time execution progress
 * using ReactFlow for the graph visualization.
 */
import { useMemo, useCallback, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  NodeProps,
  Handle,
  Position,
} from 'reactflow';
import { motion } from 'framer-motion';
import { 
  SearchOutlined, 
  UserOutlined, 
  TeamOutlined, 
  CheckCircleOutlined, 
  FileTextOutlined,
  PlayCircleOutlined,
  LoadingOutlined,
  CheckOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { Badge, Tooltip, Card, Typography } from 'antd';
import 'reactflow/dist/style.css';
import './style.css';
import type { NodeExecutionState, NodeName } from '../../types/simulation';

const { Text } = Typography;

// Node configuration
const NODE_CONFIG: Record<NodeName, {
  label: string;
  description: string;
  icon: React.ReactNode;
  position: { x: number; y: number };
}> = {
  identify_entities: {
    label: '实体识别',
    description: '识别地缘政治命题中的相关实体',
    icon: <SearchOutlined />,
    position: { x: 100, y: 100 },
  },
  profile_entities: {
    label: '实体画像',
    description: '为每个实体构建详细的政治画像',
    icon: <UserOutlined />,
    position: { x: 400, y: 100 },
  },
  coordinate_game: {
    label: '博弈推演',
    description: '执行多轮鹰鸽辩论和决策',
    icon: <TeamOutlined />,
    position: { x: 700, y: 100 },
  },
  check_completion: {
    label: '完成检查',
    description: '检查是否达到最大轮数或收敛',
    icon: <CheckCircleOutlined />,
    position: { x: 700, y: 300 },
  },
  synthesize: {
    label: '综合报告',
    description: '生成综合分析报告',
    icon: <FileTextOutlined />,
    position: { x: 1000, y: 100 },
  },
  run_simulation: {
    label: '推演执行',
    description: '整个推演流程',
    icon: <PlayCircleOutlined />,
    position: { x: -200, y: 100 },
  },
};

// Custom node component
interface WorkflowNodeData {
  label: string;
  description: string;
  icon: React.ReactNode;
  status: 'pending' | 'running' | 'completed' | 'error';
  startTime?: number;
  endTime?: number;
  details?: any;
}

function WorkflowNodeComponent({ data }: NodeProps<WorkflowNodeData>) {
  const { label, description, icon, status } = data;
  
  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <LoadingOutlined spin className="status-icon running" />;
      case 'completed':
        return <CheckOutlined className="status-icon completed" />;
      case 'error':
        return <CloseCircleOutlined className="status-icon error" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return '#1890ff';
      case 'completed':
        return '#52c41a';
      case 'error':
        return '#ff4d4f';
      default:
        return '#d9d9d9';
    }
  };

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={{ scale: 1.05 }}
      className={`workflow-node ${status}`}
      style={{
        borderColor: getStatusColor(),
        boxShadow: status === 'running' 
          ? `0 0 20px ${getStatusColor()}40`
          : `0 2px 8px ${getStatusColor()}20`,
      }}
    >
      <Handle type="target" position={Position.Left} />
      
      <Tooltip title={description} placement="top">
        <div className="node-content">
          <div 
            className="node-icon"
            style={{ backgroundColor: `${getStatusColor()}20`, color: getStatusColor() }}
          >
            {icon}
          </div>
          <div className="node-info">
            <Text strong className="node-label">{label}</Text>
            <Text type="secondary" className="node-description">{description}</Text>
          </div>
          <div className="node-status">
            {getStatusIcon()}
          </div>
        </div>
      </Tooltip>
      
      <Handle type="source" position={Position.Right} />
    </motion.div>
  );
}

const nodeTypes = {
  workflowNode: WorkflowNodeComponent,
};

interface SimulationWorkflowProps {
  nodeStates: NodeExecutionState[];
  currentNode?: NodeName | null;
  onNodeClick?: (nodeName: NodeName) => void;
}

export default function SimulationWorkflow({ 
  nodeStates, 
  currentNode,
  onNodeClick 
}: SimulationWorkflowProps) {
  // Create initial nodes
  const initialNodes: Node<WorkflowNodeData>[] = useMemo(() => {
    const nodes: Node<WorkflowNodeData>[] = [
      {
        id: 'start',
        type: 'input',
        position: { x: -50, y: 115 },
        data: { label: '开始', description: '推演开始', icon: <PlayCircleOutlined />, status: 'completed' },
        style: { 
          background: '#52c41a', 
          color: 'white',
          border: 'none',
          borderRadius: '50%',
          width: 60,
          height: 60,
        },
      },
      ...Object.entries(NODE_CONFIG).map(([key, config]) => {
        const nodeState = nodeStates.find(n => n.nodeName === key);
        return {
          id: key,
          type: 'workflowNode',
          position: config.position,
          data: {
            label: config.label,
            description: config.description,
            icon: config.icon,
            status: nodeState?.status || 'pending',
            startTime: nodeState?.startTime,
            endTime: nodeState?.endTime,
            details: nodeState?.data,
          },
        };
      }),
      {
        id: 'end',
        type: 'output',
        position: { x: 1200, y: 115 },
        data: { label: '结束', description: '推演完成', icon: <CheckOutlined />, status: 'pending' },
        style: { 
          background: '#d9d9d9', 
          color: 'white',
          border: 'none',
          borderRadius: '50%',
          width: 60,
          height: 60,
        },
      },
    ];
    return nodes;
  }, [nodeStates]);

  // Create edges
  const initialEdges: Edge[] = useMemo(() => [
    { id: 'e-start-identify', source: 'start', target: 'identify_entities', animated: true },
    { id: 'e-identify-profile', source: 'identify_entities', target: 'profile_entities', animated: true },
    { id: 'e-profile-coordinate', source: 'profile_entities', target: 'coordinate_game', animated: true },
    { id: 'e-coordinate-check', source: 'coordinate_game', target: 'check_completion', animated: true },
    { id: 'e-check-coordinate', source: 'check_completion', target: 'coordinate_game', 
      label: '继续', type: 'smoothstep', animated: true, 
      style: { stroke: '#faad14' }
    },
    { id: 'e-check-synthesize', source: 'check_completion', target: 'synthesize', 
      label: '完成', type: 'smoothstep', animated: true,
      style: { stroke: '#52c41a' }
    },
    { id: 'e-synthesize-end', source: 'synthesize', target: 'end', animated: true },
  ], []);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes when nodeStates change
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        const nodeState = nodeStates.find((n) => n.nodeName === node.id);
        if (nodeState) {
          return {
            ...node,
            data: {
              ...node.data,
              status: nodeState.status,
              startTime: nodeState.startTime,
              endTime: nodeState.endTime,
              details: nodeState.data,
            },
          };
        }
        // Update end node status based on all nodes completion
        if (node.id === 'end') {
          const allCompleted = nodeStates.length >= 5 && nodeStates.every(n => n.status === 'completed');
          return {
            ...node,
            data: { ...node.data, status: allCompleted ? 'completed' : 'pending' },
            style: { 
              ...node.style, 
              background: allCompleted ? '#52c41a' : '#d9d9d9' 
            },
          };
        }
        return node;
      })
    );
  }, [nodeStates, setNodes]);

  // Highlight current node
  useEffect(() => {
    if (currentNode) {
      setNodes((nds) =>
        nds.map((node) => ({
          ...node,
          selected: node.id === currentNode,
        }))
      );
    }
  }, [currentNode, setNodes]);

  const onNodeClickCallback = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (onNodeClick && node.id in NODE_CONFIG) {
        onNodeClick(node.id as NodeName);
      }
    },
    [onNodeClick]
  );

  return (
    <div className="simulation-workflow-container">
      <Card 
        title="推演流程可视化" 
        className="workflow-card"
        extra={
          <div className="workflow-legend">
            <Badge color="#d9d9d9" text="待执行" />
            <Badge color="#1890ff" text="执行中" />
            <Badge color="#52c41a" text="已完成" />
            <Badge color="#ff4d4f" text="错误" />
          </div>
        }
      >
        <div style={{ height: 450, width: '100%' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClickCallback}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            attributionPosition="bottom-left"
          >
            <Background color="#f0f0f0" gap={16} />
            <Controls />
            <MiniMap 
              nodeStrokeWidth={3}
              zoomable
              pannable
            />
          </ReactFlow>
        </div>
      </Card>
    </div>
  );
}
