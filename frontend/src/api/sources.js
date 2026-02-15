import api from './http'

export function listSources(params) {
  return api.get('/api/sources', { params })
}

export function createSource(payload) {
  return api.post('/api/sources', payload)
}

export function updateSource(sourceId, payload) {
  return api.put(`/api/sources/${sourceId}`, payload)
}

export function deleteSource(sourceId) {
  return api.delete(`/api/sources/${sourceId}`)
}
