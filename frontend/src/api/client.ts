/**
 * API客户端配置
 */
import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 60000, // 增加到60秒，因为AI推荐可能需要较长时间
  // 不设置默认Content-Type，让axios根据数据类型自动设置
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 如果是FormData（文件上传），不设置Content-Type，让浏览器自动设置
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 统一错误处理
    if (error.response) {
      console.error('API错误:', error.response.data)
    } else if (error.request) {
      console.error('网络错误:', error.request)
    } else {
      console.error('错误:', error.message)
    }
    return Promise.reject(error)
  }
)

export default apiClient

