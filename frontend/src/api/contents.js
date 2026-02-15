import api from './http'

export function listContents(params) {
  return api.get('/api/contents', { params })
}

export function analyzeContent(contentId) {
  return api.post(`/api/contents/${contentId}/analyze`)
}
