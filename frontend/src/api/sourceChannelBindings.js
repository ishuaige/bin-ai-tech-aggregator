import api from './http'

export function listSourceChannelBindings(params) {
  return api.get('/api/source-channel-bindings', { params })
}

export function createSourceChannelBinding(payload) {
  return api.post('/api/source-channel-bindings', payload)
}

export function deleteSourceChannelBinding(bindingId) {
  return api.delete(`/api/source-channel-bindings/${bindingId}`)
}
