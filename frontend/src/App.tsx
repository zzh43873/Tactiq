import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import Home from './pages/Home'
import Simulation from './pages/Simulation'
import Report from './pages/Report'
import Header from './components/layout/Header'
import './App.css'

const { Content, Footer } = Layout

function App() {
  return (
    <Router>
      <Layout className="app-layout">
        <Header />
        <Content className="app-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/simulation/:id" element={<Simulation />} />
            <Route path="/report/:id" element={<Report />} />
          </Routes>
        </Content>
        <Footer className="app-footer">
          地缘政治推演系统 ©2026
        </Footer>
      </Layout>
    </Router>
  )
}

export default App
