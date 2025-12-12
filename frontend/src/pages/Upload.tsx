import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import FileUpload from '../components/FileUpload'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { documentsApi } from '../api/documents'
import { useDocumentStore } from '../store/documentStore'
import { formatFileSize } from '../utils'

export default function Upload() {
  const navigate = useNavigate()
  const { setCurrentDocument } = useDocumentStore()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFileSelect = (file: File) => {
    setSelectedFile(file)
    setError(null)
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setIsUploading(true)
    setError(null)

    try {
      const response = await documentsApi.upload(selectedFile)
      setCurrentDocument(response.document_id, response.task_id)
      
      // 跳转到进度页面
      navigate(`/progress/${response.document_id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '上传失败，请重试')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <Card title="上传文档">
        <div className="space-y-6">
          <FileUpload
            onFileSelect={handleFileSelect}
            isLoading={isUploading}
          />

          {selectedFile && (
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">{formatFileSize(selectedFile.size)}</p>
                </div>
                <Button
                  onClick={handleUpload}
                  isLoading={isUploading}
                  disabled={isUploading}
                >
                  开始上传
                </Button>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div className="text-sm text-gray-500 space-y-2">
            <p className="font-medium">支持的文件格式：</p>
            <ul className="list-disc list-inside space-y-1">
              <li>PDF (.pdf)</li>
              <li>Word (.docx)</li>
              <li>PowerPoint (.pptx)</li>
              <li>Markdown (.md)</li>
              <li>纯文本 (.txt)</li>
            </ul>
            <p className="mt-2">文件大小限制：30MB</p>
          </div>
        </div>
      </Card>
    </div>
  )
}

