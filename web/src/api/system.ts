import api from './client'

export const systemApi = {
  health: () => api.get('/system/health'),
}
