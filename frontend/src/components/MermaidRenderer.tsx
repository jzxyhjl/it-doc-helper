import { useEffect, useRef, useState } from 'react'

interface MermaidRendererProps {
  chart: string
  id?: string
}

// 简单的 Mermaid 代码清理函数
function cleanMermaidCode(code: string): string {
  // 调试：输出原始代码
  console.log('原始 Mermaid 代码:', code)
  console.log('原始代码长度:', code.length)
  // 检查是否有隐藏字符或数字
  const codeArray = Array.from(code)
  const suspiciousChars = codeArray.map((c, i) => {
    const code = c.charCodeAt(0)
    if (code >= 48 && code <= 57) { // 数字 0-9
      return `位置${i}: '${c}' (${code})`
    }
    return null
  }).filter(Boolean)
  if (suspiciousChars.length > 0) {
    console.log('发现数字字符:', suspiciousChars)
  }
  
  let cleaned = code.trim()
  
  // 替换中文引号为英文引号
  cleaned = cleaned.replace(/\u201C/g, '"')  // "
  cleaned = cleaned.replace(/\u201D/g, '"')  // "
  cleaned = cleaned.replace(/\u2018/g, "'")  // '
  cleaned = cleaned.replace(/\u2019/g, "'")  // '
  cleaned = cleaned.replace(/\uFF02/g, '"')  // 全角双引号
  cleaned = cleaned.replace(/\uFF07/g, "'")  // 全角单引号
  
  // 移除 BOM 字符
  cleaned = cleaned.replace(/^\uFEFF/, '')
  
  // 修复常见问题：
  // 1. 先移除节点名后面的数字（如 SCMsg1 -> SCMsg）
  // 匹配：节点名（字母开头，包含字母数字下划线连字符）后面跟着数字，且不在标签内
  // 使用更精确的匹配，确保不会误匹配标签内的数字
  cleaned = cleaned.replace(/([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)(?=\s|$|\n|\[|-->|--|<-|==)/g, '$1')
  
  // 2. 节点定义后紧跟着的孤立节点名（如 Starter[...]SCMsg -> Starter[...]\nSCMsg）
  // 匹配：] 后面直接跟着节点名（不是 [、]、-->、-- 等）
  cleaned = cleaned.replace(/(\])([A-Z][A-Za-z0-9_\-]+)(?![\[\]<>\-|:])/g, '$1\n$2')
  
  // 3. 再次移除任何残留的数字（在节点名后面，包括标签后的数字）
  cleaned = cleaned.replace(/([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)(?=\s|$|\n|\[|-->|--|<-|==)/g, '$1')
  cleaned = cleaned.replace(/(\])([0-9]+)(?=\s|$|\n)/g, '$1')
  
  // 修复孤立节点：如果一行只有节点名没有标签也没有连接，添加默认标签
  const lines = cleaned.split('\n')
  const fixedLines: string[] = []
  
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i]
    const trimmedLine = line.trim()
    
    // 跳过空行、注释、graph 声明、subgraph、end
    if (!trimmedLine || 
        trimmedLine.startsWith('%') || 
        trimmedLine.match(/^graph\s+(TB|BT|LR|RL)/i) ||
        trimmedLine.match(/^subgraph/i) ||
        trimmedLine === 'end') {
      fixedLines.push(line)
      continue
    }
    
    // 移除无效的 direction 声明（应该在 graph 声明中，不应该单独一行）
    if (trimmedLine.match(/^direction\s+(TB|BT|LR|RL)/i)) {
      continue
    }
    
    // 检查是否是孤立的节点（只有节点名称，没有 [标签] 也没有 -->）
    // 先移除节点名后面的数字（多次处理确保移除）
    let cleanNodeName = trimmedLine
    // 移除节点名后面的数字（在标签前）
    cleanNodeName = cleanNodeName.replace(/([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)(?=\[|$|\s)/g, '$1')
    // 移除行尾的数字
    cleanNodeName = cleanNodeName.replace(/([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)\s*$/, '$1')
    // 移除标签后的数字（如 SCMsg[SCMsg]1）
    cleanNodeName = cleanNodeName.replace(/(\])([0-9]+)(?=\s|$)/g, '$1')
    
    const isolatedNodeMatch = cleanNodeName.match(/^([A-Za-z][A-Za-z0-9_\-]*?)\s*$/)
    if (isolatedNodeMatch && 
        !cleanNodeName.includes('[') && 
        !cleanNodeName.includes(']') && 
        !cleanNodeName.includes('-->') && 
        !cleanNodeName.includes('--') &&
        !cleanNodeName.includes('<-') &&
        !cleanNodeName.includes('==')) {
      // 这是一个孤立的节点，添加默认标签
      // 确保节点名中没有数字（多次处理确保彻底清理）
      let nodeName = isolatedNodeMatch[1]
      // 移除节点名中的数字（多次处理）
      nodeName = nodeName.replace(/([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)$/, '$1')
      nodeName = nodeName.replace(/([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)/g, '$1')  // 再次移除所有数字
      // 保持原有的缩进
      const indent = line.match(/^(\s*)/)?.[1] || ''
      fixedLines.push(`${indent}${nodeName}[${nodeName}]`)
    } else {
      // 再次移除标签后的数字（确保清理干净）
      const fixedLine = cleanNodeName.replace(/(\])([0-9]+)(?=\s|$)/g, '$1')
      // 保持原有的缩进
      const indent = line.match(/^(\s*)/)?.[1] || ''
      fixedLines.push(`${indent}${fixedLine}`)
    }
  }
  
  cleaned = fixedLines.join('\n')
  
  // 最后彻底清理所有数字：
  // 1. 移除标签后的数字（如 SCMsg[SCMsg]1）
  cleaned = cleaned.replace(/(\])([0-9]+)(?=\s|$|\n)/g, '$1')
  // 2. 移除节点名中的数字（如 SCMsg1[SCMsg1] -> SCMsg[SCMsg]）
  cleaned = cleaned.replace(/([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)(\[)/g, '$1$3')
  // 3. 移除行尾的孤立数字
  cleaned = cleaned.replace(/([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)(\s*$)/gm, '$1$3')
  // 4. 再次移除标签后的数字（确保彻底）
  cleaned = cleaned.replace(/(\])([0-9]+)(?=\s|$|\n)/g, '$1')
  
  // 确保代码块以换行符结尾
  if (!cleaned.endsWith('\n')) {
    cleaned += '\n'
  }
  
  return cleaned
}

export default function MermaidRenderer({ chart, id }: MermaidRendererProps) {
  const [error, setError] = useState<string | null>(null)
  const [isRendering, setIsRendering] = useState(false)
  const [svgContent, setSvgContent] = useState<string>('')
  const [cleanedCode, setCleanedCode] = useState<string>('')

  // 验证输入
  if (!chart || typeof chart !== 'string') {
    return (
      <div className="my-4 p-4 border border-yellow-300 rounded bg-yellow-50">
        <p className="text-yellow-600 font-medium">Mermaid 图表数据无效</p>
        <p className="text-yellow-500 text-sm mt-1">未提供有效的图表代码</p>
      </div>
    )
  }

  useEffect(() => {
    // 重置状态
    setError(null)
    setIsRendering(false)
    setSvgContent('')
    
    // Mermaid 的 render 方法不需要实际的 DOM 容器，只需要一个唯一的 ID
    const chartId = id || `mermaid-${Math.random().toString(36).substr(2, 9)}`
    let isMounted = true
    
    // 设置超时处理（30秒超时）
    const timeoutId = setTimeout(() => {
      if (isMounted) {
        console.error('Mermaid 渲染超时（30秒）')
        setError('渲染超时，请检查 Mermaid 代码是否正确')
        setIsRendering(false)
      }
    }, 30000)
    
    // 清理代码
    let cleaned: string
    try {
      cleaned = cleanMermaidCode(chart)
      setCleanedCode(cleaned) // 保存清理后的代码用于显示
      // 调试：输出清理后的代码
      console.log('清理后的 Mermaid 代码:', cleaned)
    } catch (e) {
      clearTimeout(timeoutId)
      if (!isMounted) return
      const errorMsg = e instanceof Error ? e.message : '代码清理失败'
      setError(errorMsg)
      setIsRendering(false)
      return
    }
    
    setIsRendering(true)
    setError(null)
    setSvgContent('')

    // 动态导入 mermaid
    import('mermaid').then((mermaidModule) => {
      if (!isMounted) {
        clearTimeout(timeoutId)
        return
      }
      
      const mermaid = mermaidModule.default
      
      // 初始化 Mermaid（只初始化一次）
      if (!(window as any).__mermaidInitialized) {
        mermaid.initialize({
          startOnLoad: false,
          theme: 'default',
          securityLevel: 'loose',
          flowchart: {
            useMaxWidth: true,
            htmlLabels: true,
            curve: 'basis'
          },
          themeVariables: {
            fontSize: '14px'
          }
        })
        ;(window as any).__mermaidInitialized = true
      }
      
      mermaid.render(chartId, cleaned).then((result) => {
        if (!isMounted) {
          clearTimeout(timeoutId)
          return
        }
        
        // 验证 SVG 内容
        if (!result || !result.svg) {
          clearTimeout(timeoutId)
          setError('渲染结果为空')
          setIsRendering(false)
          return
        }
        
        const svgText = result.svg || ''
        if (svgText.trim().length === 0) {
          clearTimeout(timeoutId)
          setError('渲染结果为空')
          setIsRendering(false)
          return
        }
        
        // 清除超时
        clearTimeout(timeoutId)
        
        // 使用 React state 来存储 SVG
        setSvgContent(svgText)
        setIsRendering(false)
      }).catch((error) => {
        clearTimeout(timeoutId)
        
        if (!isMounted) {
          return
        }
        
        // 提供更详细的错误信息
        let errorMessage = '渲染失败'
        if (error.message) {
          errorMessage = error.message
        } else if (typeof error === 'string') {
          errorMessage = error
        }
        
        setError(errorMessage)
        setIsRendering(false)
      })
    }).catch((importError) => {
      clearTimeout(timeoutId)
      
      if (!isMounted) {
        return
      }
      
      setError('Mermaid 库加载失败')
      setIsRendering(false)
    })
    
    // 清理函数
    return () => {
      clearTimeout(timeoutId)
      isMounted = false
    }
  }, [chart, id])

  if (error) {
    return (
      <div className="my-4 p-4 border border-red-300 rounded bg-red-50">
        <p className="text-red-600 font-medium">Mermaid 图表渲染失败</p>
        <p className="text-red-500 text-sm mt-1">{error}</p>
        <details className="mt-2">
          <summary className="text-sm text-gray-600 cursor-pointer">查看原始代码</summary>
          <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-x-auto whitespace-pre-wrap break-words">{chart}</pre>
        </details>
      </div>
    )
  }

  return (
    <div 
      className="mermaid-container my-4 flex justify-center overflow-x-auto bg-white p-4 rounded border border-gray-200"
      style={{ minHeight: '200px' }}
    >
      {isRendering && !svgContent && (
        <div className="flex items-center justify-center text-gray-500 w-full" style={{ minHeight: '200px' }}>
          <span>正在渲染图表...</span>
        </div>
      )}
      {!isRendering && svgContent && (
        <div 
          className="w-full flex justify-center items-center"
          style={{ minHeight: '200px' }}
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
      )}
      {!isRendering && !svgContent && !error && (
        <div className="flex items-center justify-center text-gray-400 w-full" style={{ minHeight: '200px' }}>
          <span>等待渲染...</span>
        </div>
      )}
    </div>
  )
}
