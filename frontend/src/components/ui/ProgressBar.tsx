
interface ProgressBarProps {
  progress: number
  currentStage?: string
  className?: string
}

export default function ProgressBar({ progress, currentStage, className = '' }: ProgressBarProps) {
  return (
    <div className={className}>
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-gray-700">
          {currentStage || '处理中...'}
        </span>
        <span className="text-sm font-medium text-gray-700">
          {progress}%
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className="bg-primary-600 h-2.5 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        ></div>
      </div>
    </div>
  )
}

