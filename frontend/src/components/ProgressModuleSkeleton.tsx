import Card from './ui/Card'

interface ProgressModuleSkeletonProps {
  title: string
  icon: string
  description: string
}

/**
 * 进度页面模块占位符（骨架屏）
 * 用于在视角检测完成后，显示即将生成的模块
 */
export default function ProgressModuleSkeleton({
  title,
  icon,
  description
}: ProgressModuleSkeletonProps) {
  return (
    <Card>
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{icon}</span>
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        </div>
        
        {/* 描述 */}
        <p className="text-sm text-gray-600">{description}</p>
        
        {/* 骨架屏动画 */}
        <div className="space-y-3 animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
        
        {/* 加载提示 */}
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <div className="w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
          <span>正在生成...</span>
        </div>
      </div>
    </Card>
  )
}
