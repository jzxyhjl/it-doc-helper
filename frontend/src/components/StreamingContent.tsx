import { useEffect, useState, useRef } from 'react'

interface StreamingContentProps {
  view: string
  module: string
  content: string
  className?: string
}

/**
 * 流式内容显示组件
 * 支持打字机效果，逐字显示内容
 */
export default function StreamingContent({
  view,
  module,
  content,
  className = ''
}: StreamingContentProps) {
  const [displayedContent, setDisplayedContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const contentRef = useRef('')
  const animationFrameRef = useRef<number | null>(null)

  useEffect(() => {
    // 如果内容更新，重置显示
    if (content !== contentRef.current) {
      contentRef.current = content
      setIsStreaming(true)
    }
  }, [content])

  useEffect(() => {
    if (!isStreaming) return

    let currentIndex = displayedContent.length
    const targetContent = contentRef.current

    const animate = () => {
      if (currentIndex < targetContent.length) {
        // 每次显示更多字符（模拟打字机效果）
        const chunkSize = Math.max(1, Math.floor(Math.random() * 3) + 1) // 1-3个字符
        const nextIndex = Math.min(currentIndex + chunkSize, targetContent.length)
        setDisplayedContent(targetContent.substring(0, nextIndex))
        currentIndex = nextIndex
        animationFrameRef.current = requestAnimationFrame(animate)
      } else {
        setIsStreaming(false)
      }
    }

    animationFrameRef.current = requestAnimationFrame(animate)

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [isStreaming, displayedContent.length])

  return (
    <div className={className}>
      <div className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
        {displayedContent}
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-primary-600 typing-cursor ml-1"></span>
        )}
      </div>
    </div>
  )
}

