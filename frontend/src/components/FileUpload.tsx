import React, { useCallback, useState } from 'react'
import Button from './ui/Button'
import { formatFileSize, isValidFileType } from '../utils'

interface FileUploadProps {
  onFileSelect: (file: File) => void
  maxSize?: number
  allowedTypes?: string[]
  isLoading?: boolean
}

export default function FileUpload({
  onFileSelect,
  maxSize = 30 * 1024 * 1024, // 30MB
  allowedTypes = ['pdf', 'docx', 'pptx', 'md', 'txt'],
  isLoading = false
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validateFile = (file: File): string | null => {
    const fileExt = file.name.split('.').pop()?.toLowerCase() || ''
    
    // 特殊处理：检测 .doc 格式并提供友好提示
    if (fileExt === 'doc') {
      return '系统暂不支持 .doc 格式（旧版 Word 文档）。请使用 Microsoft Word 或 LibreOffice 将文件另存为 .docx 格式后重新上传。'
    }
    
    if (!isValidFileType(file.name, allowedTypes)) {
      return `不支持的文件类型。支持的类型: ${allowedTypes.join(', ').toUpperCase()}`
    }
    if (file.size > maxSize) {
      return `文件大小超过限制 (${formatFileSize(maxSize)})。建议拆分后处理。`
    }
    // 警告阈值：20MB
    const warningThreshold = 20 * 1024 * 1024
    if (file.size > warningThreshold) {
      // 不阻止上传，但会在控制台记录警告
      console.warn(`文件较大 (${formatFileSize(file.size)})，处理时间可能较长`)
    }
    return null
  }

  const handleFile = useCallback((file: File) => {
    setError(null)
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      return
    }
    onFileSelect(file)
  }, [onFileSelect, maxSize, allowedTypes])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }, [handleFile])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }, [handleFile])

  return (
    <div className="w-full">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-gray-400'
        } ${isLoading ? 'opacity-50 pointer-events-none' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-upload"
          className="hidden"
          accept={allowedTypes.map(t => `.${t}`).join(',')}
          onChange={handleChange}
          disabled={isLoading}
        />
        <label htmlFor="file-upload" className="cursor-pointer">
          <div className="flex flex-col items-center">
            <svg
              className="w-12 h-12 text-gray-400 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-gray-600 mb-2">
              <span className="text-primary-600 font-medium">点击上传</span> 或拖拽文件到此处
            </p>
            <p className="text-sm text-gray-500">
              支持 {allowedTypes.join(', ').toUpperCase()} 格式，最大 {formatFileSize(maxSize)}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              提示：如使用旧版 Word 文档（.doc），请先转换为 .docx 格式
            </p>
          </div>
        </label>
      </div>
      {error && (
        <div className="mt-2 text-sm text-red-600">{error}</div>
      )}
    </div>
  )
}

