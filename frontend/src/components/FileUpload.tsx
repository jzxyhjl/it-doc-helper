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
  maxSize = 15 * 1024 * 1024, // 15MB（最大限制）
  allowedTypes = ['pdf', 'docx', 'pptx', 'md', 'txt'],
  isLoading = false
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)

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
    // 警告阈值：12MB（低于最大限制15MB，提前提醒用户）
    const warningThreshold = 12 * 1024 * 1024
    if (file.size > warningThreshold && file.size <= maxSize) {
      // 返回警告信息（不阻止上传，但会在UI显示提示）
      return `WARNING:${formatFileSize(file.size)}` // 使用特殊前缀标识警告
    }
    return null
  }

  const handleFile = useCallback((file: File) => {
    setError(null)
    setWarning(null)
    const validationError = validateFile(file)
    if (validationError) {
      // 检查是否是警告（以WARNING:开头）
      if (validationError.startsWith('WARNING:')) {
        const fileSize = validationError.replace('WARNING:', '')
        setWarning(`文件较大 (${fileSize})，处理时间可能较长，建议控制在12MB以下以获得最佳体验`)
        // 警告不阻止上传，继续处理
        onFileSelect(file)
      } else {
        // 真正的错误，阻止上传
        setError(validationError)
        return
      }
    } else {
      onFileSelect(file)
    }
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
              支持 {allowedTypes.join(', ').toUpperCase()} 格式，最大 {formatFileSize(maxSize)}，<span className="text-yellow-700">建议 12MB 以下</span>
            </p>
            <p className="text-xs text-gray-400 mt-1">
              提示：如使用旧版 Word 文档（.doc），请先转换为 .docx 格式
            </p>
          </div>
        </label>
      </div>
      {warning && (
        <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <p className="text-sm text-yellow-800">{warning}</p>
          </div>
        </div>
      )}
      {error && (
        <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-600 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
      )}
    </div>
  )
}

