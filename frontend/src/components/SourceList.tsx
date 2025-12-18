/**
 * 来源片段列表组件
 */
import { useState } from 'react'

interface Source {
  id: number
  text: string
  position?: number
}

interface SourceListProps {
  sources: Source[]
  collapsed?: boolean  // 是否默认折叠
  maxLength?: number   // 文本最大显示长度
}

export default function SourceList({ 
  sources, 
  collapsed = false,
  maxLength = 300 
}: SourceListProps) {
  const [isExpanded, setIsExpanded] = useState(!collapsed)

  // 异常处理：数据验证
  if (!sources || !Array.isArray(sources) || sources.length === 0) {
    return null
  }

  // 过滤无效的source
  const validSources = sources.filter(
    (source) => source && source.id && source.text && typeof source.text === 'string'
  )

  if (validSources.length === 0) {
    return null
  }

  const truncateText = (text: string) => {
    if (!text || typeof text !== 'string') return ''
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  return (
    <div className="mt-3 border-t border-gray-200 pt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center text-sm text-gray-600 hover:text-gray-900 mb-2"
      >
        <span className="mr-1">
          {isExpanded ? '▼' : '▶'}
        </span>
        <span>来源片段 ({sources.length})</span>
      </button>
      
      {isExpanded && (
        <div className="space-y-2 mt-2">
          {validSources.map((source) => (
            <div
              key={source.id}
              className="bg-gray-50 rounded p-3 text-sm border-l-2 border-primary-300"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-500">
                  段落 {source.id}
                </span>
              </div>
              <p className="text-gray-700 leading-relaxed">
                {truncateText(source.text)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

