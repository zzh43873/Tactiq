/**
 * WebSocket服务
 * 提供实时进度推送
 */

import { useEffect, useRef, useState, useCallback } from 'react'

interface WebSocketMessage {
  type: 'status' | 'progress' | 'error' | 'pong'
  data?: any
  message?: string
}

interface UseWebSocketOptions {
  taskType: 'simulation' | 'intelligence'
  taskId: string | null
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket({
  taskType,
  taskId,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null)
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (!taskId) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    // 构建WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/${taskType}/${taskId}`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log(`WebSocket connected: ${taskType}/${taskId}`)
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
        onConnect?.()

        // 启动心跳
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000) // 30秒心跳
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          onMessage?.(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onclose = () => {
        console.log(`WebSocket disconnected: ${taskType}/${taskId}`)
        setIsConnected(false)
        onDisconnect?.()

        // 清理心跳
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }

        // 自动重连
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++
          console.log(`Reconnecting... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`)
          reconnectTimerRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        onError?.(error)
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
    }
  }, [taskType, taskId, onMessage, onConnect, onDisconnect, onError, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    // 停止重连
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }

    // 清理心跳
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }

    // 关闭连接
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
      return true
    }
    return false
  }, [])

  const requestStatus = useCallback(() => {
    return sendMessage({ type: 'get_status' })
  }, [sendMessage])

  // 自动连接/断开
  useEffect(() => {
    if (taskId) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
  }, [taskId, connect, disconnect])

  return {
    isConnected,
    lastMessage,
    connect,
    disconnect,
    sendMessage,
    requestStatus
  }
}

// 兼容旧版轮询的Hook（渐进式迁移）
export function useSimulationProgress(
  simulationId: string | null,
  options?: {
    useWebSocket?: boolean
    pollInterval?: number
    onProgress?: (progress: number, status: string) => void
    onComplete?: (result: any) => void
    onError?: (error: string) => void
  }
) {
  const {
    useWebSocket: useWs = true,
    pollInterval = 5000,
    onProgress,
    onComplete,
    onError
  } = options || {}

  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('pending')
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  // WebSocket连接
  const { lastMessage, isConnected } = useWebSocket({
    taskType: 'simulation',
    taskId: useWs ? simulationId : null,
    onMessage: (message) => {
      if (message.type === 'progress' || message.type === 'status') {
        const data = message.data
        if (data) {
          setProgress(data.progress || 0)
          setStatus(data.status || 'pending')
          onProgress?.(data.progress || 0, data.status || 'pending')

          if (data.status === 'completed' && data.result) {
            setResult(data.result)
            onComplete?.(data.result)
          }

          if (data.status === 'failed' && data.error) {
            setError(data.error)
            onError?.(data.error)
          }
        }
      }
    }
  })

  // 降级到轮询（当WebSocket不可用时）
  useEffect(() => {
    if (!simulationId || (useWs && isConnected)) return

    const poll = async () => {
      try {
        const response = await fetch(`/api/v1/simulation/${simulationId}`)
        if (!response.ok) {
          if (response.status === 404) {
            setError('推演任务不存在')
            onError?.('推演任务不存在')
            return
          }
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        setProgress(data.progress || 0)
        setStatus(data.status || 'pending')
        onProgress?.(data.progress || 0, data.status || 'pending')

        if (data.status === 'completed' && data.result) {
          setResult(data.result)
          onComplete?.(data.result)
        }

        if (data.status === 'failed' && data.error) {
          setError(data.error)
          onError?.(data.error)
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }

    poll()
    const interval = setInterval(poll, pollInterval)

    return () => clearInterval(interval)
  }, [simulationId, useWs, isConnected, pollInterval, onProgress, onComplete, onError])

  return {
    progress,
    status,
    result,
    error,
    isConnected,
    isLoading: status !== 'completed' && status !== 'failed'
  }
}

export default useWebSocket
