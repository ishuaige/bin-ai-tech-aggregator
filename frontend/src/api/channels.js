import api from './http'

export function listChannels(params) {
  return api.get('/api/channels', { params })
}

export function createChannel(payload) {
  return api.post('/api/channels', payload)
}

export function updateChannel(channelId, payload) {
  return api.put(`/api/channels/${channelId}`, payload)
}

export function deleteChannel(channelId) {
  return api.delete(`/api/channels/${channelId}`)
}
