import api from './client'

export const knowledgeApi = {
  search: (kw: string) => api.get('/knowledge/search', { params: { kw } }),
  skillFrequency: (topN: number = 15) => api.get('/knowledge/skill-frequency', { params: { top_n: topN } }),
  versions: () => api.get('/knowledge/versions'),
}
