/**
 * Round Visualization Component
 * 
 * Displays round-by-round hawk vs dove debate and decision visualization
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Card,
  Tag,
  Typography,
  Progress,
  Badge,
  Empty,
  Tabs,
  Timeline,
  Avatar,
  Divider,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  FireOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  AimOutlined,
  SafetyOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import './style.css';
import type { RoundVisualization, EntityDecision } from '../../types/simulation';

const { Text, Title, Paragraph } = Typography;
const { TabPane } = Tabs;

interface RoundVisualizationProps {
  rounds: RoundVisualization[];
  currentRound?: number | null;
}

// Hawk/Dove debate display component
function DebateView({ decision }: { decision: EntityDecision }) {
  return (
    <div className="debate-container">
      <div className="debate-sides">
        {/* Hawk Side */}
        <motion.div 
          className="debate-side hawk"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="debate-header">
            <FireOutlined className="debate-icon" />
            <Text strong className="debate-title">鹰派观点</Text>
          </div>
          <div className="debate-content">
            {decision.debate?.hawkArgument ? (
              <Paragraph>{decision.debate.hawkArgument}</Paragraph>
            ) : (
              <Text type="secondary">正在生成鹰派论点...</Text>
            )}
          </div>
        </motion.div>

        <Divider type="vertical" className="debate-divider" />

        {/* Dove Side */}
        <motion.div 
          className="debate-side dove"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="debate-header">
            <SafetyOutlined className="debate-icon" />
            <Text strong className="debate-title">鸽派观点</Text>
          </div>
          <div className="debate-content">
            {decision.debate?.doveArgument ? (
              <Paragraph>{decision.debate.doveArgument}</Paragraph>
            ) : (
              <Text type="secondary">正在生成鸽派论点...</Text>
            )}
          </div>
        </motion.div>
      </div>

      {/* Final Decision */}
      <motion.div 
        className="final-decision"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Divider>
          <Tag color="blue" icon={<CheckCircleOutlined />}>最终决策</Tag>
        </Divider>
        <div className="decision-content">
          <Text strong className="decision-action">{decision.actionContent}</Text>
          {decision.reasoning && (
            <Paragraph type="secondary" className="decision-reasoning">
              {decision.reasoning}
            </Paragraph>
          )}
        </div>
      </motion.div>
    </div>
  );
}

// Decision card component
function DecisionCard({ 
  decision, 
  index 
}: { 
  decision: EntityDecision; 
  index: number;
}) {
  const getStatusColor = () => {
    switch (decision.status) {
      case 'decided':
        return 'success';
      case 'debating':
        return 'processing';
      default:
        return 'default';
    }
  };

  const getActionTypeIcon = (actionType: string) => {
    switch (actionType?.toLowerCase()) {
      case 'military':
        return <AimOutlined />;
      case 'diplomatic':
        return <GlobalOutlined />;
      case 'economic':
        return <SafetyOutlined />;
      default:
        return <CheckCircleOutlined />;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Card 
        size="small" 
        className={`decision-card ${decision.status}`}
        title={
          <div className="decision-card-header">
            <Avatar 
              size="small" 
              style={{ 
                backgroundColor: decision.status === 'decided' ? '#52c41a' : '#1890ff' 
              }}
            >
              {decision.entityName.charAt(0)}
            </Avatar>
            <Text strong>{decision.entityName}</Text>
            <Badge status={getStatusColor() as any} />
          </div>
        }
        extra={
          decision.actionType && (
            <Tag icon={getActionTypeIcon(decision.actionType)} color="blue">
              {decision.actionType}
            </Tag>
          )
        }
      >
        {decision.status === 'decided' ? (
          <div className="decision-summary">
            <Paragraph ellipsis={{ rows: 2 }}>{decision.actionContent}</Paragraph>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic 
                  title="信心度" 
                  value={decision.confidence * 100} 
                  suffix="%" 
                  precision={0}
                  valueStyle={{ fontSize: 14 }}
                />
              </Col>
              <Col span={12}>
                <Statistic 
                  title="国际风险" 
                  value={(decision.internationalRisk || 0) * 100} 
                  suffix="%" 
                  precision={0}
                  valueStyle={{ 
                    fontSize: 14, 
                    color: (decision.internationalRisk || 0) > 0.5 ? '#ff4d4f' : '#52c41a'
                  }}
                />
              </Col>
            </Row>
          </div>
        ) : (
          <div className="decision-pending">
            <DebateView decision={decision} />
          </div>
        )}
      </Card>
    </motion.div>
  );
}

// Round card component
function RoundCard({ 
  round, 
  isActive 
}: { 
  round: RoundVisualization; 
  isActive: boolean;
}) {
  const [activeTab, setActiveTab] = useState('overview');

  const completionRate = round.decisions.length > 0
    ? (round.decisions.filter(d => d.status === 'decided').length / round.decisions.length) * 100
    : 0;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`round-card ${isActive ? 'active' : ''}`}
    >
      <Card
        title={
          <div className="round-card-header">
            <Title level={5} className="round-title">
              第 {round.roundNumber} 轮推演
              {isActive && <Badge status="processing" style={{ marginLeft: 8 }} />}
            </Title>
            <Tag color={round.status === 'completed' ? 'success' : 'processing'}>
              {round.status === 'completed' ? '已完成' : '进行中'}
            </Tag>
          </div>
        }
        extra={
          <Text type="secondary">
            {round.decisions.filter(d => d.status === 'decided').length} / {round.decisions.length} 决策完成
          </Text>
        }
      >
        <Progress 
          percent={Math.round(completionRate)} 
          status={round.status === 'completed' ? 'success' : 'active'}
          className="round-progress"
        />

        <Tabs activeKey={activeTab} onChange={setActiveTab} className="round-tabs">
          <TabPane 
            tab={<span><TeamOutlined /> 决策概览</span>} 
            key="overview"
          >
            <div className="decisions-grid">
              {round.decisions.map((decision, index) => (
                <DecisionCard 
                  key={decision.entityName} 
                  decision={decision} 
                  index={index}
                />
              ))}
            </div>
          </TabPane>
          
          <TabPane 
            tab={<span><ClockCircleOutlined /> 详细过程</span>} 
            key="details"
          >
            <Timeline mode="left" className="round-timeline">
              {round.decisions.map((decision) => (
                <Timeline.Item
                  key={decision.entityName}
                  dot={
                    decision.status === 'decided' 
                      ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
                      : <ClockCircleOutlined style={{ color: '#1890ff' }} />
                  }
                >
                  <Text strong>{decision.entityName}</Text>
                  <Paragraph type="secondary">{decision.actionContent}</Paragraph>
                  {decision.reasoning && (
                    <div className="reasoning-detail">
                      <Text type="secondary">决策理由：</Text>
                      <Paragraph>{decision.reasoning}</Paragraph>
                    </div>
                  )}
                </Timeline.Item>
              ))}
            </Timeline>
          </TabPane>
        </Tabs>

        {round.situationSummary && (
          <div className="situation-summary">
            <Divider orientation="left">局势更新</Divider>
            <Paragraph>{round.situationSummary}</Paragraph>
          </div>
        )}
      </Card>
    </motion.div>
  );
}

export default function RoundVisualization({ 
  rounds, 
  currentRound 
}: RoundVisualizationProps) {
  if (rounds.length === 0) {
    return (
      <Card title="推演轮次" className="round-visualization-card">
        <Empty description="暂无推演轮次数据" />
      </Card>
    );
  }

  return (
    <Card 
      title="推演轮次详情" 
      className="round-visualization-card"
      extra={
        <div className="round-stats">
          <Tag color="blue">{rounds.length} 轮推演</Tag>
          <Tag color="green">
            {rounds.filter(r => r.status === 'completed').length} 轮完成
          </Tag>
        </div>
      }
    >
      <div className="rounds-container">
        <AnimatePresence>
          {rounds.map((round) => (
            <RoundCard
              key={round.roundNumber}
              round={round}
              isActive={currentRound === round.roundNumber}
            />
          ))}
        </AnimatePresence>
      </div>
    </Card>
  );
}
