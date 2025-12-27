import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { historyApi } from '../api/history'
import type { DocumentHistoryResponse, DocumentHistoryItem } from '../types'

export default function History() {
  const navigate = useNavigate()
  const [history, setHistory] = useState<DocumentHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [documentType, setDocumentType] = useState<string>('')
  const [searchKeyword, setSearchKeyword] = useState<string>('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [batchDeleting, setBatchDeleting] = useState(false)
  const pageSize = 20

  useEffect(() => {
    fetchHistory()
  }, [page, documentType, searchKeyword])

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const data = await historyApi.getHistory({
        page,
        page_size: pageSize,
        document_type: documentType || undefined,
        search: searchKeyword || undefined
      })
      setHistory(data)
      // 清空选择（因为数据已更新）
      setSelectedIds(new Set())
    } catch (err: any) {
      setError(err.response?.data?.detail || '获取历史记录失败')
    } finally {
      setLoading(false)
    }
  }

  const handleViewResult = (documentId: string) => {
    navigate(`/result/${documentId}`)
  }

  const handleDelete = async (documentId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('确定要删除这条记录吗？')) return

    try {
      const { documentsApi } = await import('../api/documents')
      await documentsApi.delete(documentId)
      fetchHistory() // 刷新列表
    } catch (err: any) {
      alert(err.response?.data?.detail || '删除失败')
    }
  }

  const handleToggleSelect = (documentId: string, e?: React.MouseEvent | React.ChangeEvent) => {
    if (e) {
      e.stopPropagation()
    }
    const newSelected = new Set(selectedIds)
    if (newSelected.has(documentId)) {
      newSelected.delete(documentId)
    } else {
      newSelected.add(documentId)
    }
    setSelectedIds(newSelected)
  }

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked && history) {
      setSelectedIds(new Set(history.items.map(item => item.document_id)))
    } else {
      setSelectedIds(new Set())
    }
  }

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) {
      alert('请先选择要删除的记录')
      return
    }

    if (!confirm(`确定要删除选中的 ${selectedIds.size} 条记录吗？此操作不可恢复。`)) {
      return
    }

    setBatchDeleting(true)
    try {
      const { documentsApi } = await import('../api/documents')
      const result = await documentsApi.batchDelete(Array.from(selectedIds))
      
      if (result.failed_count > 0) {
        alert(`删除完成：成功 ${result.success_count} 条，失败 ${result.failed_count} 条`)
      } else {
        alert(`成功删除 ${result.success_count} 条记录`)
      }
      
      setSelectedIds(new Set())
      fetchHistory() // 刷新列表
    } catch (err: any) {
      alert(err.response?.data?.detail || '批量删除失败')
    } finally {
      setBatchDeleting(false)
    }
  }

  const getTypeLabel = (type?: string) => {
    const labels: Record<string, string> = {
      interview: '面试题',
      technical: '技术文档',
      architecture: '架构文档'
    }
    return labels[type || ''] || '未知'
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: '等待处理',
      processing: '处理中',
      completed: '已完成',
      failed: '处理失败'
    }
    return labels[status] || status
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800'
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  if (loading && !history) {
    return (
      <div className="max-w-6xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-gray-600">加载中...</p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">处理历史</h2>
        <Button onClick={() => navigate('/upload')}>上传新文档</Button>
      </div>

      {/* 筛选器和搜索 */}
      <Card>
        <div className="flex items-center space-x-4 flex-wrap gap-4">
          <div className="flex items-center space-x-2 flex-1 min-w-[200px]">
            <label className="text-sm font-medium text-gray-700 whitespace-nowrap">文件名搜索:</label>
            <input
              type="text"
              value={searchKeyword}
              onChange={(e) => {
                setSearchKeyword(e.target.value)
                setPage(1)
              }}
              placeholder="输入文件名关键词..."
              className="flex-1 border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 whitespace-nowrap">文档类型:</label>
            <select
              value={documentType}
              onChange={(e) => {
                setDocumentType(e.target.value)
                setPage(1)
              }}
              className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">全部</option>
              <option value="interview">面试题</option>
              <option value="technical">技术文档</option>
              <option value="architecture">架构文档</option>
            </select>
          </div>
        </div>
      </Card>

      {/* 批量操作栏 */}
      {history && history.items.length > 0 && (
        <Card>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedIds.size > 0 && selectedIds.size === history.items.length}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">
                  全选 ({selectedIds.size > 0 ? `已选择 ${selectedIds.size} 项` : '未选择'})
                </span>
              </label>
            </div>
            {selectedIds.size > 0 && (
              <Button
                variant="danger"
                size="sm"
                onClick={handleBatchDelete}
                disabled={batchDeleting}
              >
                {batchDeleting ? '删除中...' : `批量删除 (${selectedIds.size})`}
              </Button>
            )}
          </div>
        </Card>
      )}

      {error && (
        <Card>
          <div className="text-red-600">{error}</div>
        </Card>
      )}

      {history && (
        <>
          <Card>
            <div className="space-y-4">
              {history.items.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  暂无历史记录
                </div>
              ) : (
                <div className="space-y-3">
                  {history.items.map((item: DocumentHistoryItem) => (
                    <div
                      key={item.document_id}
                      className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3 flex-1">
                          <input
                            type="checkbox"
                            checked={selectedIds.has(item.document_id)}
                            onChange={(e) => {
                              e.stopPropagation()
                              handleToggleSelect(item.document_id, e)
                            }}
                            className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 cursor-pointer"
                          />
                          <div 
                            className="flex-1 cursor-pointer"
                            onClick={() => item.status === 'completed' && handleViewResult(item.document_id)}
                          >
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="font-medium text-gray-900">{item.filename}</h3>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                              {getStatusLabel(item.status)}
                            </span>
                            {item.document_type && (
                              <span className="px-2 py-1 bg-primary-100 text-primary-800 rounded-full text-xs">
                                {getTypeLabel(item.document_type)}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center space-x-4 text-sm text-gray-500">
                            <span>类型: {item.file_type.toUpperCase()}</span>
                            {item.processing_time && (
                              <span>处理时间: {item.processing_time}秒</span>
                            )}
                            <span>上传时间: {new Date(item.upload_time).toLocaleString('zh-CN')}</span>
                          </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          {item.status === 'completed' && (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleViewResult(item.document_id)
                              }}
                            >
                              查看结果
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={(e) => handleDelete(item.document_id, e)}
                          >
                            删除
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>

          {/* 分页 */}
          {history.total > pageSize && (
            <Card>
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  共 {history.total} 条记录，第 {page} / {Math.ceil(history.total / pageSize)} 页
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    上一页
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setPage(p => Math.min(Math.ceil(history.total / pageSize), p + 1))}
                    disabled={page >= Math.ceil(history.total / pageSize)}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

