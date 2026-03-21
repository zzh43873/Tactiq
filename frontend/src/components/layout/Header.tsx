import { Link, useLocation } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import { HomeOutlined, GlobalOutlined, FileTextOutlined, RadarChartOutlined } from '@ant-design/icons'

const { Header: AntHeader } = Layout

function Header() {
  const location = useLocation()
  
  const items = [
    {
      key: 'home',
      icon: <HomeOutlined />,
      label: <Link to="/">首页</Link>,
    },
    {
      key: 'simulations',
      icon: <GlobalOutlined />,
      label: <Link to="/">推演列表</Link>,
    },
    {
      key: 'reports',
      icon: <FileTextOutlined />,
      label: <Link to="/">报告</Link>,
    },
  ]
  
  const currentKey = location.pathname === '/' ? 'home' : 
                     location.pathname.includes('simulation') ? 'simulations' : 'home'

  return (
    <AntHeader 
      style={{ 
        background: '#fff', 
        padding: 0,
        borderBottom: '1px solid #e8e8e8',
        position: 'sticky',
        top: 0,
        zIndex: 1000,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)'
      }}
    >
      <div 
        style={{ 
          float: 'left', 
          width: 240, 
          textAlign: 'center',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          gap: '10px'
        }}
      >
        <RadarChartOutlined 
          style={{ 
            fontSize: 28, 
            color: '#1890ff'
          }} 
        />
        <h2 
          style={{ 
            margin: 0, 
            color: '#1890ff',
            fontSize: '1.4rem',
            fontWeight: 700
          }}
        >
          Tactiq
        </h2>
      </div>
      <Menu
        mode="horizontal"
        selectedKeys={[currentKey]}
        items={items}
        style={{ 
          flex: 1, 
          minWidth: 0,
          background: 'transparent',
          borderBottom: 'none'
        }}
        theme="light"
      />
    </AntHeader>
  )
}

export default Header
