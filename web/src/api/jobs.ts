import api from './client'

export const jobsApi = {
  list: (params: Record<string, any> = {}) => api.get('/jobs', { params }),
  sources: () => api.get('/jobs/sources'),
}
