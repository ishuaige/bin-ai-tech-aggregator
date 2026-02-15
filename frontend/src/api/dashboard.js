import api from './http'

export function fetchOverview() {
  return api.get('/api/dashboard/overview')
}
