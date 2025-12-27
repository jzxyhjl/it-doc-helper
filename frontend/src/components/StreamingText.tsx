import { useEffect, useState, useRef } from 'react'

interface StreamingTextProps {
  documentId: string
  prompt: string
  systemPrompt?: string
  view?: string
  onComplete?: (fullContent: string) => void
  className?: string
}

/**
 * 流式文本生成组件
 * 类似deepseek-chat的逐字输出效果
 */
export default function StreamingText({
  documentId,
  prompt,
  systemPrompt,
  view,
  onComplete,
  className = ''
}: StreamingTextProps) {
  const [content, setContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!documentId || !prompt) return

    // 构建SSE URL
    const params = new URLSearchParams({
      prompt,
      ...(systemPrompt && { system_prompt: systemPrompt }),
      ...(view && { view })
    })
    const url = `/api/v1/streaming/${documentId}/generate-text?${params.toString()}`

    // 创建EventSource连接
    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    setIsStreaming(true)
    setContent('')
    setError(null)

    // 处理消息
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === 'start') {
          // 开始生成
          setContent('')
        } else if (data.type === 'chunk') {
          // 接收文本块，追加到内容
          setContent(prev => prev + (data.content || ''))
        } else if (data.type === 'done') {
          // 生成完成
          setIsStreaming(false)
          if (data.full_content) {
            setContent(data.full_content)
          }
          if (onComplete && data.full_content) {
            onComplete(data.full_content)
          }
          eventSource.close()
        } else if (data.type === 'error') {
          // 错误
          setError(data.error || '生成失败')
          setIsStreaming(false)
          eventSource.close()
        }
      } catch (err) {
        console.error('解析SSE消息失败:', err)
        setError('数据解析失败')
        setIsStreaming(false)
        eventSource.close()
      }
    }

    // 处理错误
    eventSource.onerror = (err) => {
      console.error('SSE连接错误:', err)
      setError('连接失败，请重试')
      setIsStreaming(false)
      eventSource.close()
    }

    // 清理函数
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
    }
  }, [documentId, prompt, systemPrompt, view, onComplete])

  return (
    <div className={className}>
      {error && (
        <div className="text-red-600 text-sm mb-2">
          错误: {error}
        </div>
      )}
      <div className="whitespace-pre-wrap">
        {content}
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-primary-600 animate-pulse ml-1">|</span>
        )}
      </div>
    </div>
  )
}

