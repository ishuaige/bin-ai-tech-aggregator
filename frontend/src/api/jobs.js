import api from './http'

export function runNowJob() {
  return api.post('/api/jobs/run-now')
}

export function fetchRunNowStatus(jobId) {
  return api.get(`/api/jobs/run-now/${jobId}`)
}
