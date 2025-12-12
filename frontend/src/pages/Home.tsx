import { useNavigate } from 'react-router-dom'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          IT学习辅助系统
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          智能文档处理，助力IT学习
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <div className="text-center">
            <div className="text-4xl mb-4">📄</div>
            <h3 className="font-semibold text-gray-900 mb-2">文档上传</h3>
            <p className="text-sm text-gray-600 mb-4">
              支持PDF、Word、PPT等多种格式
            </p>
            <Button onClick={() => navigate('/upload')} size="sm">
              开始上传
            </Button>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-4xl mb-4">📊</div>
            <h3 className="font-semibold text-gray-900 mb-2">智能处理与学习辅助</h3>
            <p className="text-sm text-gray-600 mb-4">
              自动识别文档类型，提供智能处理和学习建议
            </p>
            <Button variant="secondary" onClick={() => navigate('/history')} size="sm">
              查看历史记录
            </Button>
          </div>
        </Card>
      </div>

      <Card>
        <h3 className="font-semibold text-gray-900 mb-4">功能特性</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
          <div className="flex items-start">
            <span className="text-primary-600 mr-2">✓</span>
            <span>面试题文档：内容总结、问题生成、答案提取</span>
          </div>
          <div className="flex items-start">
            <span className="text-primary-600 mr-2">✓</span>
            <span>技术文档：前置条件、学习路径、方法建议</span>
          </div>
          <div className="flex items-start">
            <span className="text-primary-600 mr-2">✓</span>
            <span>架构文档：配置流程、组件视图、白话串讲</span>
          </div>
          <div className="flex items-start">
            <span className="text-primary-600 mr-2">✓</span>
            <span>实时进度：WebSocket实时推送处理进度</span>
          </div>
        </div>
      </Card>
    </div>
  )
}

