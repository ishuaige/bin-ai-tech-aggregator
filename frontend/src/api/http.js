import axios from 'axios'
import { ElMessage } from 'element-plus'
import { beginRequest, endRequest } from '../composables/uiFeedback'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 20000,
})

api.interceptors.request.use(
  (config) => {
    beginRequest()
    return config
  },
  (error) => {
    endRequest()
    return Promise.reject(error)
  },
)

api.interceptors.response.use(
  (response) => {
    endRequest()
    const payload = response.data
    if (payload?.code !== 0) {
      const businessError = new Error(payload?.message || '请求失败')
      businessError.response = response
      throw businessError
    }
    return payload.data
  },
  (error) => {
    endRequest()
    const detail = error?.response?.data?.message
    const message = detail || error.message || '网络请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default api
