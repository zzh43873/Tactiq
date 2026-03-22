/**
 * Execution Timeline Component
 * 
 * Displays a vertical timeline of simulation execution steps
 * with real-time progress indicators and expandable details.
 */
import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Timeline,
  Card,
  Tag,
  Typography,
  Badge,
  Spin,
  Empty,
  Tooltip,
} from 'antd';
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SearchOutlined,
  UserOutlined,
  TeamOutlined,
  FileTextOutlined,
  CheckOutlined,
  DownOutlined,
  RightOutlined,
} from '@ant-design/icons';
import './style.css';
import type { 
  NodeExecutionState, 
  RoundVisualization, 
  TimelineItem,
  NodeName 
} from '../../types/simulation';

const { Text } = Typography;

interface ExecutionTimelineProps {
  nodeStates: NodeExecutionState[];
  rounds: RoundVisualization[];
  simulationStartTime?: number;
  simulationEndTime?: number;
  status: 'running' | 'completed' | 'error';
  error?: string;
}

// Node display configuration
const NODE_DISPLAY_CONFIG: Record<NodeName, {
  title: string;
  icon: React.ReactNode;
  color: string;
}> = {
  identify_entities: {
    title: '实体识别',
    icon: <SearchOutlined />,
    color: '#1890ff',
  },
  profile_entities: {
    title: '实体画像',
    icon: <UserOutlined />,
    color: '#52c41a',
  },
  coordinate_game: {
    title: '博弈推演',
    icon: <TeamOutlined />,
    color: '#faad14',
  },
  check_completion: {
    title: '完成检查',
    icon: <CheckOutlined />,
    color: '#722ed1',
  },
  synthesize: {
    title: '综合报告',
    icon: <FileTextOutlined />,
    color: '#eb2f96',
  },
  run_simulation: {
    title: '推演执行',
    icon: <PlayCircleOutlined />,
    color: '#13c2c2',
  },
};

export default function ExecutionTimeline({
  nodeStates,
  rounds,
  simulationStartTime,
  simulationEndTime,
  status,
  error,
}: ExecutionTimelineProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  // Build timeline items from node states and rounds
  const timelineItems = useMemo((): TimelineItem[] => {
    const items: TimelineItem[] = [];

    // Add simulation start milestone
    if (simulationStartTime) {
      items.push({
        id: 'start',
        type: 'milestone',
        title: '推演开始',
        description: '启动推演流程',
        timestamp: simulationStartTime,
        status: 'completed',
        icon: 'play',
      });
    }

    // Add node execution items
    nodeStates.forEach((node) => {
      const config = NODE_DISPLAY_CONFIG[node.nodeName];
      if (!config) return;

      items.push({
        id: `node-${node.nodeName}`,
        type: 'node',
        title: config.title,
        description: getNodeDescription(node),
        timestamp: node.startTime || Date.now(),
        status: node.status,
        duration: node.duration,
        details: node.data,
        icon: node.nodeName,
      });

      // Add round items for coordinate_game node
      if (node.nodeName === 'coordinate_game' && rounds.length > 0) {
        rounds.forEach((round) => {
          items.push({
            id: `round-${round.roundNumber}`,
            type: 'round',
            title: `第 ${round.roundNumber} 轮推演`,
            description: round.situationSummary || '执行鹰鸽辩论决策',
            timestamp: round.startTime || Date.now(),
            status: round.status,
            duration: round.endTime && round.startTime 
              ? round.endTime - round.startTime 
              : undefined,
            details: round,
            icon: 'round',
          });

          // Add decision items for each entity in the round
          round.decisions.forEach((decision) => {
            items.push({
              id: `decision-${round.roundNumber}-${decision.entityName}`,
              type: 'decision',
              title: `${decision.entityName} 决策`,
              description: decision.actionContent,
              timestamp: Date.now(),
              status: decision.status === 'decided' ? 'completed' : 'pending',
              details: decision,
              icon: 'decision',
            });
          });
        });
      }
    });

    // Sort by timestamp
    items.sort((a, b) => a.timestamp - b.timestamp);

    // Add simulation end milestone
    if (simulationEndTime || status === 'completed' || status === 'error') {
      items.push({
        id: 'end',
        type: 'milestone',
        title: status === 'error' ? '推演失败' : '推演完成',
        description: error || '推演流程结束',
        timestamp: simulationEndTime || Date.now(),
        status: status === 'error' ? 'error' : 'completed',
        icon: status === 'error' ? 'error' : 'complete',
      });
    }

    return items;
  }, [nodeStates, rounds, simulationStartTime, simulationEndTime, status, error]);

  function getNodeDescription(node: NodeExecutionState): string {
    switch (node.nodeName) {
      case 'identify_entities':
        return node.data?.entity_count 
          ? `识别到 ${node.data.entity_count} 个实体` 
          : '识别相关实体';
      case 'profile_entities':
        return node.data?.profiles_completed
          ? `完成 ${node.data.profiles_completed} 个实体画像`
          : '构建实体画像';
      case 'coordinate_game':
        return node.data?.round_number
          ? `执行第 ${node.data.round_number} 轮推演`
          : '执行博弈推演';
      case 'check_completion':
        return node.data?.is_complete
          ? '推演完成'
          : '继续下一轮';
      case 'synthesize':
        return node.data?.report_length
          ? `生成 ${node.data.report_length} 字报告`
          : '生成综合报告';
      default:
        return '';
    }
  }

  function formatDuration(ms?: number): string {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  }

  function getStatusIcon(itemStatus: string) {
    switch (itemStatus) {
      case 'running':
        return <Spin size="small" />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  }

  function getStatusColor(itemStatus: string): string {
    switch (itemStatus) {
      case 'running':
        return '#1890ff';
      case 'completed':
        return '#52c41a';
      case 'error':
        return '#ff4d4f';
      default:
        return '#d9d9d9';
    }
  }

  function renderTimelineDot(item: TimelineItem) {
    const color = getStatusColor(item.status);
    
    if (item.type === 'milestone') {
      return (
        <div 
          className="timeline-dot milestone"
          style={{ background: color, borderColor: color }}
        >
          {item.icon === 'play' && <PlayCircleOutlined style={{ color: 'white' }} />}
          {item.icon === 'complete' && <CheckCircleOutlined style={{ color: 'white' }} />}
          {item.icon === 'error' && <CloseCircleOutlined style={{ color: 'white' }} />}
        </div>
      );
    }

    return (
      <div 
        className={`timeline-dot ${item.status}`}
        style={{ borderColor: color }}
      >
        {getStatusIcon(item.status)}
      </div>
    );
  }

  function renderItemContent(item: TimelineItem) {
    const isExpanded = expandedNodes.has(item.id);
    const hasDetails = item.details && Object.keys(item.details).length > 0;

    return (
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className={`timeline-item ${item.type}`}
      >
        <Card 
          size="small" 
          className={`timeline-card ${item.status}`}
          onClick={() => {
            if (hasDetails) {
              const newExpanded = new Set(expandedNodes);
              if (isExpanded) {
                newExpanded.delete(item.id);
              } else {
                newExpanded.add(item.id);
              }
              setExpandedNodes(newExpanded);
            }
          }}
          style={{ cursor: hasDetails ? 'pointer' : 'default' }}
        >
          <div className="timeline-item-header">
            <div className="timeline-item-title">
              <Text strong>{item.title}</Text>
              {item.duration && (
                <Tag color="default">
                  {formatDuration(item.duration)}
                </Tag>
              )}
            </div>
            <div className="timeline-item-actions">
              {item.status === 'running' && (
                <Badge status="processing" text="执行中" />
              )}
              {hasDetails && (
                isExpanded ? <DownOutlined /> : <RightOutlined />
              )}
            </div>
          </div>
          
          {item.description && (
            <Text type="secondary" className="timeline-item-description">
              {item.description}
            </Text>
          )}

          <AnimatePresence>
            {isExpanded && hasDetails && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="timeline-item-details"
              >
                <pre className="details-json">
                  {JSON.stringify(item.details, null, 2)}
                </pre>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      </motion.div>
    );
  }

  if (timelineItems.length === 0) {
    return (
      <Card title="执行时间线" className="execution-timeline-card">
        <Empty description="暂无执行记录" />
      </Card>
    );
  }

  return (
    <Card 
      title="执行时间线" 
      className="execution-timeline-card"
      extra={
        <div className="timeline-stats">
          <Tag color="blue">{nodeStates.filter(n => n.status === 'completed').length} / {nodeStates.length} 节点完成</Tag>
          {rounds.length > 0 && (
            <Tag color="orange">{rounds.length} 轮推演</Tag>
          )}
        </div>
      }
    >
      <Timeline mode="left" className="execution-timeline">
        {timelineItems.map((item) => (
          <Timeline.Item
            key={item.id}
            dot={renderTimelineDot(item)}
            label={
              <Tooltip title={new Date(item.timestamp).toLocaleString()}>
                <Text type="secondary" className="timeline-time">
                  {new Date(item.timestamp).toLocaleTimeString()}
                </Text>
              </Tooltip>
            }
          >
            {renderItemContent(item)}
          </Timeline.Item>
        ))}
      </Timeline>
    </Card>
  );
}
