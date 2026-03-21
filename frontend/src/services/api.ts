import axios from 'axios'

// 创建axios实例
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 推演相关API
export const simulationApi = {
  // 启动推演
  start: (data: { event_description: string; config?: any }) =>
    api.post('/simulation/run', data),
  
  // 获取推演状态
  getStatus: (id: string) => api.get(`/simulation/${id}`),
  
  // 获取推演列表
  list: (params?: { page?: number; page_size?: number }) =>
    api.get('/simulation', { params }),
}

// 情报相关API
export const intelligenceApi = {
  // 收集情报
  collect: (data: { event_description: string; time_range?: string; sources?: string[] }) =>
    api.post('/intelligence/collect', data),
  
  // 获取情报任务状态
  getTaskStatus: (taskId: string) => api.get(`/intelligence/task/${taskId}`),
}

// 实体相关API
export const entityApi = {
  // 获取实体列表
  list: (params?: { page?: number; page_size?: number; entity_type?: string }) =>
    api.get('/entities', { params }),
  
  // 获取实体详情
  get: (id: string) => api.get(`/entities/${id}`),
}

export default api
