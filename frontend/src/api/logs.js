import api from './http'

export function listLogs(params) {
  return api.get('/api/logs', { params })
}

export function getLogDetail(logId) {
  return api.get(`/api/logs/${logId}`)
}
