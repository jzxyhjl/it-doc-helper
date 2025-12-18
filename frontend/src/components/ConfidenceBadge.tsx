/**
 * 可信度标签组件
 */
interface ConfidenceBadgeProps {
  label?: '高' | '中' | '低' | string
  score?: number
}

export default function ConfidenceBadge({ label, score }: ConfidenceBadgeProps) {
  // 异常处理：如果label和score都缺失，返回null
  if (!label && score === undefined) {
    return null
  }

  // 根据score推断label（如果label缺失）
  const getLabel = (): string => {
    if (label) return label
    if (score === undefined) return '未知'
    if (score >= 75) return '高'
    if (score >= 40) return '中'
    return '低'
  }

  const getColorClass = () => {
    const finalLabel = getLabel()
    const finalScore = score ?? 50
    
    if (finalLabel === '高' || finalScore >= 75) {
      return 'bg-green-100 text-green-800 border-green-300'
    } else if (finalLabel === '中' || finalScore >= 40) {
      return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    } else {
      return 'bg-red-100 text-red-800 border-red-300'
    }
  }

  const displayLabel = getLabel()

  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getColorClass()}`}
      title={score !== undefined ? `可信度: ${score.toFixed(1)}` : undefined}
    >
      {displayLabel}
      {score !== undefined && !isNaN(score) && (
        <span className="ml-1 text-xs opacity-75">({score.toFixed(0)})</span>
      )}
    </span>
  )
}

