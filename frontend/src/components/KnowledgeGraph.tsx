/**
 * 知识图谱组件（已废弃）
 * @deprecated 功能暂时移除，保留代码以备将来使用
 */
import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Card from './ui/Card'
import LoadingSpinner from './ui/LoadingSpinner'
import apiClient from '../api/client'

interface KnowledgeGraphProps {
  similarityThreshold?: number
  maxNodes?: number
  documentType?: string
  documentId?: string
  title?: string
}

interface GraphNode {
  id: string
  label: string
  type: string
  filename?: string
  file_type?: string
  content_summary?: string
  quality_score?: number
  upload_time?: string
  frequency?: number
  color: string
  size: number
  layer?: string
  layer_name?: string
  layer_order?: number
  description?: string
  position?: string
}

interface GraphEdge {
  source: string
  target: string
  similarity?: number
  cooccurrence?: number
  weight: number
  label: string
  documents_count?: number
  type?: string
  relationship_strength?: number
  description?: string
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  total_nodes: number
  total_edges: number
  similarity_threshold?: number
  cooccurrence_threshold?: number
  generated_at: string
  error?: string
  summary?: string
  architecture_layers?: Record<string, string>
}

export default function KnowledgeGraph({
  similarityThreshold = 0.3,
  maxNodes = 50,
  documentType,
  documentId,
  title = "知识图谱"
}: KnowledgeGraphProps) {
  const navigate = useNavigate()
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const cytoscapeRef = useRef<any>(null)

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        const params = new URLSearchParams()
        params.append('similarity_threshold', similarityThreshold.toString())
        params.append('max_nodes', maxNodes.toString())
        if (documentType) {
          params.append('document_type', documentType)
        }
        if (documentId) {
          params.append('document_id', documentId)
        }
        
        const url = `/learning/knowledge-graph?${params.toString()}`
        const response = await apiClient.get(url)
        setGraphData(response.data)
      } catch (err: any) {
        setError(err.response?.data?.detail || '获取知识图谱失败')
      } finally {
        setLoading(false)
      }
    }

    fetchGraphData()
  }, [similarityThreshold, maxNodes, documentType, documentId])

  useEffect(() => {
    if (!graphData || !containerRef.current || graphData.nodes.length === 0) {
      return
    }

    // 动态导入 Cytoscape
    import('cytoscape').then((cytoscape) => {
      // @ts-ignore - cytoscape-cose-bilkent 没有类型定义
      import('cytoscape-cose-bilkent').then((coseBilkent) => {
        cytoscape.default.use(coseBilkent.default)
        
        // 如果有架构层次，先加载 dagre 布局，然后再创建实例
        const loadLayouts = graphData.architecture_layers
          ? // @ts-ignore - cytoscape-dagre 没有类型定义
            import('cytoscape-dagre').then((dagre) => {
              // @ts-ignore - cytoscape-dagre 没有类型定义
              cytoscape.default.use(dagre.default)
            }).catch((err) => {
              // dagre 加载失败，使用默认布局
              console.warn('dagre layout not available, using cose-bilkent', err)
            })
          : Promise.resolve()
        
        loadLayouts.then(() => {
          // 准备 Cytoscape 数据格式
          const elements = [
            ...graphData.nodes.map((node) => ({
              data: {
                id: node.id,
                label: node.label,
                type: node.type,
                filename: node.filename,
                content_summary: node.content_summary,
                quality_score: node.quality_score,
                color: node.color,
                size: node.size,
                layer: node.layer,
                layer_name: node.layer_name,
                layer_order: node.layer_order,
                description: node.description,
                position: node.position
              }
            })),
            ...graphData.edges.map((edge) => ({
              data: {
                id: `${edge.source}-${edge.target}`,
                source: edge.source,
                target: edge.target,
                similarity: edge.similarity,
                weight: edge.weight,
                label: edge.label || edge.description || '',
                type: edge.type,
                relationship_strength: edge.relationship_strength,
                description: edge.description
              }
            }))
          ]

          // 如果容器已存在，先清理
          if (containerRef.current) {
            containerRef.current.innerHTML = ''
            
            // 创建 Cytoscape 实例
            const cy = cytoscape.default({
              container: containerRef.current,
              // @ts-ignore - elements类型兼容性问题，但实际运行正常
              elements: elements,
              style: [
                {
                  selector: 'node',
                  style: {
                  'width': 'data(size)',
                  'height': 'data(size)',
                  'background-color': 'data(color)',
                  'border-width': 2,
                  'border-color': '#fff',
                  'label': 'data(label)',
                  'font-size': (node: any) => {
                    const size = node.data('size') || 30
                    // 字体大小基于节点大小：最小10px，最大16px
                    return `${Math.max(10, Math.min(16, size * 0.4))}px`
                  },
                  'text-valign': 'center',
                  'text-halign': 'center',
                  'color': '#fff',
                  'text-outline-width': 2,
                  'text-outline-color': 'data(color)',
                  'text-wrap': 'wrap',
                  'text-max-width': (node: any) => {
                    const size = node.data('size') || 30
                    return `${size * 1.2}px`
                  },
                    'overlay-opacity': 0
                  }
                },
                {
                  selector: 'edge',
                  style: {
                  'width': (edge: any) => {
                    const weight = edge.data('weight') || 0.3
                    // 边宽度基于权重：最小1px，最大5px
                    return Math.max(1, Math.min(5, weight * 5))
                  },
                  'line-color': (edge: any) => {
                    const relType = edge.data('type')
                    const strength = edge.data('relationship_strength') || 0.3
                    
                    // 根据关系类型设置颜色
                    if (relType === 'dependency') return '#ef4444' // 红色 - 依赖关系
                    if (relType === 'call') return '#3b82f6' // 蓝色 - 调用关系
                    if (relType === 'dataflow') return '#10b981' // 绿色 - 数据流
                    if (relType === 'integration') return '#8b5cf6' // 紫色 - 集成关系
                    
                    // 默认基于强度
                    if (strength >= 0.7) return '#3b82f6'
                    if (strength >= 0.5) return '#60a5fa'
                    if (strength >= 0.3) return '#94a3b8'
                    return '#cbd5e1'
                  },
                  'target-arrow-color': (edge: any) => {
                    const relType = edge.data('type')
                    const strength = edge.data('relationship_strength') || 0.3
                    
                    if (relType === 'dependency') return '#ef4444'
                    if (relType === 'call') return '#3b82f6'
                    if (relType === 'dataflow') return '#10b981'
                    if (relType === 'integration') return '#8b5cf6'
                    
                    if (strength >= 0.7) return '#3b82f6'
                    if (strength >= 0.5) return '#60a5fa'
                    if (strength >= 0.3) return '#94a3b8'
                    return '#cbd5e1'
                  },
                  'target-arrow-shape': 'triangle',
                  'curve-style': 'bezier',
                  'label': 'data(label)',
                  'font-size': '11px',
                  'font-weight': 'bold',
                  'text-background-color': '#fff',
                  'text-background-opacity': 0.9,
                  'text-border-color': '#94a3b8',
                  'text-border-width': 1,
                    'text-border-opacity': 0.5
                  }
                }
              ],
              layout: (() => {
                // 如果有架构层次，尝试使用 dagre 布局（层次化布局）
                if (graphData.architecture_layers) {
                  return {
                    name: 'dagre',
                    rankDir: 'TB', // 从上到下
                    nodeSep: 50,
                    edgeSep: 20,
                    rankSep: 100,
                    animate: true,
                    animationDuration: 1500
                  } as any
                }
                // 否则使用 cose-bilkent（力导向布局）
                return {
                  name: 'cose-bilkent',
                  idealEdgeLength: 150,
                  nodeRepulsion: 6000,
                  edgeElasticity: 0.5,
                  nestingFactor: 0.1,
                  gravity: 0.2,
                  numIter: 3000,
                  tile: true,
                  randomize: false,
                  componentSpacing: 40,
                  animate: true,
                  animationDuration: 1500
                } as any
              })(),
              // 禁用滚轮缩放
              wheelSensitivity: 0,
              // 禁用双击缩放
              boxSelectionEnabled: false
            })
            
            // 禁用滚轮事件
            cy.on('wheel', (evt: any) => {
              evt.cy.preventDefault()
              evt.originalEvent.preventDefault()
              evt.originalEvent.stopPropagation()
            })

            // 节点点击事件（如果是技术名词，显示详细信息；如果是文档，跳转）
            cy.on('tap', 'node', (evt: any) => {
              const nodeData = evt.target.data()
              // 只有文档节点才跳转，技术名词节点显示信息
              if (nodeData.type !== 'technology' && nodeData.filename) {
                navigate(`/result/${nodeData.id}`)
              } else if (nodeData.type === 'technology') {
                // 显示技术节点信息
                const node = graphData.nodes.find(n => n.id === nodeData.id)
                if (node) {
                  setSelectedNode(node)
                  setSelectedEdge(null)
                }
              }
            })
            
            // 边点击事件，显示关系信息
            cy.on('tap', 'edge', (evt: any) => {
              const edgeData = evt.target.data()
              const edge = graphData.edges.find(e => 
                e.source === edgeData.source && e.target === edgeData.target
              )
              if (edge) {
                setSelectedEdge(edge)
                setSelectedNode(null)
              }
            })
            
            // 点击空白处取消选择
            cy.on('tap', (evt: any) => {
              if (evt.target === cy) {
                setSelectedNode(null)
                setSelectedEdge(null)
              }
            })

            cytoscapeRef.current = cy
          }
        })
      }).catch((err) => {
        // 静默处理加载错误（可选：在生产环境中记录到错误追踪服务）
        // console.error('Failed to load cose-bilkent:', err)
        setError('知识图谱布局算法加载失败')
      })
    }).catch((err) => {
      // 静默处理加载错误（可选：在生产环境中记录到错误追踪服务）
      // console.error('Failed to load Cytoscape:', err)
      setError('知识图谱可视化组件加载失败，请确保已安装 cytoscape 和 cytoscape-cose-bilkent')
    })

    return () => {
      if (cytoscapeRef.current) {
        cytoscapeRef.current.destroy()
        cytoscapeRef.current = null
      }
    }
  }, [graphData, navigate])

  if (loading) {
    return (
      <Card title={title}>
        <div className="text-center py-8">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-gray-600">加载知识图谱中...</p>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card title={title}>
        <div className="text-center py-8 text-red-500">
          {error}
        </div>
      </Card>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <Card title={title}>
        <div className="text-center py-8 text-gray-500">
          暂无知识图谱数据
        </div>
      </Card>
    )
  }

  const getDocumentTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      interview: '面试题',
      technical: '技术文档',
      architecture: '架构文档',
      unknown: '未知'
    }
    return labels[type] || type
  }

  return (
    <Card title={title}>
      {graphData.summary && (
        <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-sm text-blue-900">{graphData.summary}</p>
        </div>
      )}
      <div className="mb-4 text-sm text-gray-600">
        <div className="flex items-center justify-between mb-2">
          <span>技术节点数: {graphData.total_nodes} | 关联数: {graphData.total_edges}</span>
          {graphData.architecture_layers && (
            <div className="flex items-center gap-2 flex-wrap">
              {Object.entries(graphData.architecture_layers).map(([key, name]) => {
                const layerColors: Record<string, string> = {
                  'application': '#3B82F6',
                  'middleware': '#10B981',
                  'framework': '#F59E0B',
                  'infrastructure': '#8B5CF6',
                  'database': '#EF4444',
                  'other': '#6B7280'
                }
                return (
                  <span
                    key={key}
                    className="text-xs px-2 py-1 rounded"
                    style={{
                      backgroundColor: layerColors[key] || '#6B7280',
                      color: '#fff'
                    }}
                  >
                    {name}
                  </span>
                )
              })}
            </div>
          )}
        </div>
        {graphData.architecture_layers ? (
          <p className="text-xs mt-2 text-gray-500">
            提示：点击节点查看详细信息，点击边查看关系说明。节点颜色表示架构层次，箭头表示上下游关系。
          </p>
        ) : (
          <p className="text-xs mt-2 text-gray-500">
            提示：节点大小表示技术出现频率，边表示技术之间的共现关系，拖动节点可调整布局
          </p>
        )}
      </div>
      <div className="relative">
        <div
          ref={containerRef}
          className="w-full border border-gray-200 rounded-lg"
          style={{ height: '600px', minHeight: '400px' }}
        />
        {/* 节点信息弹窗 */}
        {selectedNode && (
          <div className="absolute top-4 right-4 bg-white border border-gray-300 rounded-lg shadow-lg p-4 max-w-sm z-10">
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-semibold text-gray-900">{selectedNode.label}</h4>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            {selectedNode.layer_name && (
              <div className="mb-2">
                <span className="text-xs text-gray-500">架构层次：</span>
                <span
                  className="ml-2 text-xs px-2 py-1 rounded text-white"
                  style={{ backgroundColor: selectedNode.color }}
                >
                  {selectedNode.layer_name}
                </span>
              </div>
            )}
            {selectedNode.position && (
              <div className="mb-2">
                <span className="text-xs text-gray-500">位置作用：</span>
                <p className="text-xs text-gray-700 mt-1">{selectedNode.position}</p>
              </div>
            )}
            {selectedNode.description && (
              <div>
                <span className="text-xs text-gray-500">技术描述：</span>
                <p className="text-xs text-gray-700 mt-1">{selectedNode.description}</p>
              </div>
            )}
          </div>
        )}
        {/* 边信息弹窗 */}
        {selectedEdge && (
          <div className="absolute top-4 right-4 bg-white border border-gray-300 rounded-lg shadow-lg p-4 max-w-sm z-10">
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-semibold text-gray-900">关系信息</h4>
              <button
                onClick={() => setSelectedEdge(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            <div className="mb-2">
              <span className="text-xs text-gray-500">关系：</span>
              <span className="ml-2 text-sm font-medium text-gray-900">
                {selectedEdge.source} → {selectedEdge.target}
              </span>
            </div>
            {selectedEdge.type && (
              <div className="mb-2">
                <span className="text-xs text-gray-500">关系类型：</span>
                <span className="ml-2 text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">
                  {selectedEdge.type === 'dependency' ? '依赖关系' :
                   selectedEdge.type === 'call' ? '调用关系' :
                   selectedEdge.type === 'dataflow' ? '数据流' :
                   selectedEdge.type === 'integration' ? '集成关系' : selectedEdge.type}
                </span>
              </div>
            )}
            {selectedEdge.description && (
              <div>
                <span className="text-xs text-gray-500">关系说明：</span>
                <p className="text-xs text-gray-700 mt-1">{selectedEdge.description}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
