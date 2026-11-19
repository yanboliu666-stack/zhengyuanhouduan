import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 5000
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface RealtimeState {
  junction_id: string
  current_phase_id: string
  mode: string
  degradation: string
  tick_id?: number | string
  last_updated?: number
  signal_colors?: {
    north_through: string
    south_through: string
    east_through: string
    west_through: string
  }
  lanes?: Record<string, any>
  vehicleCount?: number
  avgSpeed?: number
  queueLength?: number
  delayTime?: number
  level?: string
}

// 1. 命名导出（解决 SignalControl.vue 和其他页面的解构引入报错）
export const getIntersections = () => {
  return Promise.resolve({
    data: {
      code: 200,
      data: [
        { id: 'mini_1', name: 'mini_1 (边缘端智能机)' },
        { id: 'INT_001', name: 'INT_001 (中山路与解放路)' },
        { id: 'INT_002', name: 'INT_002 (人民路与建设路)' }
      ]
    }
  })
}

export const getRealtimeData = (id: string) => {
  return api.get(`/realtime/${id}`)
}

export const getJunctionRealtimeState = (id: string) => {
  return api.get(`/realtime/state/${id}`)
}

export const getCongestion = (id: string) => {
  return api.get(`/analytics/congestion/${id}`)
}

export const getAlerts = (id: string) => {
  return api.get(`/alerts/${id}`)
}

export const resolveAlert = (alertId: number | string) => {
  return api.put(`/alerts/${alertId}/resolve`)
}

export const calcWebster = (data: { junctionId: string; totalLostTime: number; flows: number[] }) => {
  return api.post('/control/webster/calculate', data)
}

export const dispatchSignal = (data: { junctionId: string; cycleLength: number; greenTimes: Record<string, number> }) => {
  return api.post('/dispatch/timing-plan', data)
}

export const login = (data: any) => {
  return api.post('/auth/login', data)
}

// 2. 对象封装导出（兼容 trafficApi.xxx 调用方式）
export const trafficApi = {
  login,
  getIntersections,
  getRealtimeData,
  getJunctionRealtimeState,
  getCongestion,
  getAlerts,
  resolveAlert,
  calcWebster,
  dispatchSignal
}

export default trafficApi