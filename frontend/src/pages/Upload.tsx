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

    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/eeaccba4-a712-43c7-b379-db4639c44cbf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Upload.tsx:22',message:'handleUpload started',data:{fileName:selectedFile.name,fileSize:selectedFile.size,fileType:selectedFile.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion

    try {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/eeaccba4-a712-43c7-b379-db4639c44cbf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Upload.tsx:29',message:'Before API call',data:{fileName:selectedFile.name},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      const response = await documentsApi.upload(selectedFile)
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/eeaccba4-a712-43c7-b379-db4639c44cbf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Upload.tsx:31',message:'API call succeeded',data:{documentId:response.document_id,taskId:response.task_id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
      // #endregion
      setCurrentDocument(response.document_id, response.task_id)
      
      // 跳转到进度页面
      navigate(`/progress/${response.document_id}`)
    } catch (err: any) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/eeaccba4-a712-43c7-b379-db4639c44cbf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Upload.tsx:35',message:'API call failed',data:{error:err.message,status:err.response?.status,statusText:err.response?.statusText,detail:err.response?.data?.detail,code:err.code},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
      setError(err.response?.data?.detail || err.message || '上传失败，请重试')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <Card title="上传文档">
        <div className="space-y-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-blue-800">
              📝 我们会先理解文档说了什么，然后和你一起规划学习路径
            </p>
          </div>
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
                  开始分析
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
            <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-yellow-800 font-medium">⚠️ 格式提示</p>
              <p className="text-yellow-700 text-xs mt-1">
                暂不支持旧版 Word 文档（.doc）。如使用 .doc 格式，请使用 Microsoft Word 或 LibreOffice 将文件另存为 .docx 格式后重新上传。
              </p>
            </div>
            <p className="mt-2">
              文件大小限制：最大 15MB，<span className="text-yellow-700 font-medium">建议 12MB 以下</span>以获得最佳体验
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}

