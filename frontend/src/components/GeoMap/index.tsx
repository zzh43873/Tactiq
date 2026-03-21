import { useState, useMemo, useEffect } from 'react'
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup,
} from 'react-simple-maps'
import { Card, Tag, Space, Typography, Tooltip, Alert, Spin } from 'antd'
import { FireOutlined, GlobalOutlined, TeamOutlined, ClockCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import './style.css'

const { Text } = Typography

// 世界地图 TopoJSON - 使用多个备选源
const GEO_URLS = [
  'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json',
  'https://unpkg.com/world-atlas@2.0.2/countries-110m.json',
  '/world-atlas/countries-110m.json', // 本地备选
]

interface MapEvent {
  id: string
  entity: string
  action: string
  dimension: 'military' | 'economic' | 'diplomatic' | 'public_opinion'
  timeframe: 'short' | 'medium' | 'long'
  location: { lat: number; lng: number; name: string }
  impact: number
  description: string
}

interface GeoMapProps {
  events: MapEvent[]
  selectedEventId?: string
  onEventClick?: (event: MapEvent) => void
}

// 实体位置数据库（主要国家和热点地区）
const entityLocations: Record<string, { lat: number; lng: number }> = {
  '美国': { lat: 39.8283, lng: -98.5795 },
  '中国': { lat: 35.8617, lng: 104.1954 },
  '俄罗斯': { lat: 61.5240, lng: 105.3188 },
  '伊朗': { lat: 32.4279, lng: 53.6880 },
  '以色列': { lat: 31.0461, lng: 34.8516 },
  '沙特阿拉伯': { lat: 23.8859, lng: 45.0792 },
  '叙利亚': { lat: 34.8021, lng: 38.9968 },
  '黎巴嫩': { lat: 33.8547, lng: 35.8623 },
  '也门': { lat: 15.5527, lng: 48.5164 },
  '伊拉克': { lat: 33.2232, lng: 43.6793 },
  '阿富汗': { lat: 33.9391, lng: 67.7100 },
  '巴基斯坦': { lat: 30.3753, lng: 69.3451 },
  '印度': { lat: 20.5937, lng: 78.9629 },
  '朝鲜': { lat: 40.3399, lng: 127.5101 },
  '韩国': { lat: 35.9078, lng: 127.7669 },
  '日本': { lat: 36.2048, lng: 138.2529 },
  '欧盟': { lat: 50.8503, lng: 4.3517 },
  '英国': { lat: 55.3781, lng: -3.4360 },
  '法国': { lat: 46.2276, lng: 2.2137 },
  '德国': { lat: 51.1657, lng: 10.4515 },
  '土耳其': { lat: 38.9637, lng: 35.2433 },
  '埃及': { lat: 26.8206, lng: 30.8025 },
  '乌克兰': { lat: 48.3794, lng: 31.1656 },
  '台湾': { lat: 23.6978, lng: 120.9605 },
  '南海': { lat: 12.0, lng: 115.0 },
  '霍尔木兹海峡': { lat: 26.5, lng: 56.3 },
  '红海': { lat: 20.0, lng: 38.0 },
  '加沙': { lat: 31.5, lng: 34.47 },
  '约旦河西岸': { lat: 32.0, lng: 35.3 },
}

export default function GeoMap({ events, selectedEventId, onEventClick }: GeoMapProps) {
  const [zoom, setZoom] = useState(1)
  const [center, setCenter] = useState<[number, number]>([0, 20])
  const [geoUrlIndex, setGeoUrlIndex] = useState(0)
  const [mapError, setMapError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const geoUrl = GEO_URLS[geoUrlIndex]

  // 处理地图加载错误
  const handleGeoError = () => {
    if (geoUrlIndex < GEO_URLS.length - 1) {
      setGeoUrlIndex(prev => prev + 1)
    } else {
      setMapError('地图数据加载失败，请检查网络连接')
      setIsLoading(false)
    }
  }

  // 处理地图加载成功
  const handleGeoLoad = () => {
    setIsLoading(false)
    setMapError(null)
  }

  const dimensionColors = {
    military: '#ff4d4f',
    economic: '#52c41a',
    diplomatic: '#1890ff',
    public_opinion: '#faad14',
  }

  const dimensionIcons = {
    military: <FireOutlined />,
    economic: <GlobalOutlined />,
    diplomatic: <TeamOutlined />,
    public_opinion: <ClockCircleOutlined />,
  }

  // 为事件补充地理位置
  const eventsWithLocation = useMemo(() => {
    return events.map(event => {
      if (event.location) return event
      
      // 尝试从实体名称匹配位置
      for (const [entity, coords] of Object.entries(entityLocations)) {
        if (event.entity.includes(entity) || entity.includes(event.entity)) {
          return { ...event, location: { ...coords, name: entity } }
        }
      }
      
      return event
    }).filter(event => event.location)
  }, [events])

  // 计算地图中心点
  const focusOnEvent = (event: MapEvent) => {
    if (event.location) {
      setCenter([event.location.lng, event.location.lat])
      setZoom(4)
      onEventClick?.(event)
    }
  }

  return (
    <Card 
      className="geo-map-container" 
      title="地缘政治态势地图"
      extra={
        <Space>
          <Tag color="#ff4d4f"><FireOutlined /> 军事</Tag>
          <Tag color="#52c41a"><GlobalOutlined /> 经济</Tag>
          <Tag color="#1890ff"><TeamOutlined /> 外交</Tag>
          <Tag color="#faad14"><ClockCircleOutlined /> 舆论</Tag>
        </Space>
      }
    >
      <div className="geo-map-wrapper">
        {isLoading && (
          <div className="geo-map-loading">
            <Spin tip="加载地图数据..." />
          </div>
        )}
        {mapError && (
          <Alert
            message="地图加载失败"
            description={mapError}
            type="error"
            showIcon
            action={
              <ReloadOutlined 
                style={{ cursor: 'pointer' }} 
                onClick={() => {
                  setGeoUrlIndex(0)
                  setMapError(null)
                  setIsLoading(true)
                }}
              />
            }
          />
        )}
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{
            scale: 140,
            center: [0, 25],
          }}
          style={{ width: '100%', height: '100%', background: '#e8f4f8' }}
        >
          <ZoomableGroup
            zoom={zoom}
            center={center}
            minZoom={1}
            maxZoom={8}
            onMoveEnd={({ coordinates, zoom }) => {
              setCenter(coordinates as [number, number])
              setZoom(zoom)
            }}
          >
            <Geographies 
              geography={geoUrl}
              onError={handleGeoError}
              onLoad={handleGeoLoad}
            >
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#ffffff"
                    stroke="#1890ff"
                    strokeWidth={0.3}
                    style={{
                      default: { 
                        outline: 'none',
                        fill: '#f0f9ff',
                        stroke: '#91caff',
                        strokeWidth: 0.5
                      },
                      hover: { 
                        fill: '#bae0ff', 
                        outline: 'none',
                        stroke: '#4096ff',
                        strokeWidth: 0.8
                      },
                      pressed: { outline: 'none' },
                    }}
                  />
                ))
              }
            </Geographies>

            {eventsWithLocation.map((event) => (
              <Marker
                key={event.id}
                coordinates={[event.location!.lng, event.location!.lat]}
                onClick={() => focusOnEvent(event)}
              >
                <Tooltip
                  title={
                    <div>
                      <Text strong>{event.entity}</Text>
                      <br />
                      <Text>{event.action}</Text>
                      <br />
                      <Tag color={dimensionColors[event.dimension]}>
                        {dimensionIcons[event.dimension]}
                        {event.dimension}
                      </Tag>
                    </div>
                  }
                >
                  <g
                    className={`map-marker ${selectedEventId === event.id ? 'selected' : ''}`}
                    style={{ cursor: 'pointer' }}
                  >
                    <circle
                      r={8 + event.impact * 5}
                      fill={dimensionColors[event.dimension]}
                      opacity={0.6}
                      className="marker-pulse"
                    />
                    <circle
                      r={4}
                      fill={dimensionColors[event.dimension]}
                      stroke="#fff"
                      strokeWidth={2}
                    />
                  </g>
                </Tooltip>
              </Marker>
            ))}
          </ZoomableGroup>
        </ComposableMap>
      </div>

      {eventsWithLocation.length > 0 && (
        <div className="geo-map-legend">
          <Text type="secondary">
            共 {eventsWithLocation.length} 个事件，点击标记查看详情
          </Text>
        </div>
      )}
    </Card>
  )
}
