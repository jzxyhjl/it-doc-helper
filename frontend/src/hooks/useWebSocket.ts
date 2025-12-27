/**
 * WebSocket Hook
 */
import { useEffect, useRef, useState } from 'react'

interface UseWebSocketOptions {
  url: string
  onMessage?: (data: any) => void
  onError?: (error: Event) => void
  onClose?: () => void
}

export function useWebSocket({ url, onMessage, onError, onClose }: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!url) return

    let ws: WebSocket | null = null

    try {
      // 构建WebSocket URL
      // 如果url已经是完整路径（以/开头），使用当前协议和主机
      let wsUrl: string
      if (url.startsWith('/')) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        wsUrl = `${protocol}//${window.location.host}${url}`
      } else {
        // 否则，将 http:// 转换为 ws://，https:// 转换为 wss://
        wsUrl = url.replace('http://', 'ws://').replace('https://', 'wss://')
      }
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessage?.(data)
        } catch (error) {
          console.error('WebSocket消息解析错误:', error)
        }
      }

      ws.onerror = (error) => {
        onError?.(error)
      }

      ws.onclose = () => {
        setIsConnected(false)
        onClose?.()
      }

      wsRef.current = ws
    } catch (error) {
      console.error('WebSocket连接失败:', error)
      onError?.(error as Event)
    }

    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [url, onMessage, onError, onClose])

  const send = (data: any) => {
    if (wsRef.current && isConnected) {
      wsRef.current.send(JSON.stringify(data))
    }
  }

  return { isConnected, send }
}

