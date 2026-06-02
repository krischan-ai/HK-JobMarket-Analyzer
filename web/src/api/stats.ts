import api from './client'

export const statsApi = {
  overview: () => api.get('/stats/overview'),
  topSkills: (topN: number = 15) => api.get('/stats/top-skills', { params: { top_n: topN } }),
  categories: () => api.get('/stats/categories'),
  salaryByLocation: () => api.get('/stats/salary-by-location'),
  sourceDistribution: () => api.get('/stats/source-distribution'),
  locationDistribution: () => api.get('/stats/location-distribution'),
  dashboard: () => api.get('/stats/dashboard'),
  roleDistribution: () => api.get('/stats/role-distribution'),
  roleSalary: () => api.get('/stats/role-salary'),
  llmStatus: () => api.get('/stats/llm-status'),
  runClassification: (batchSize: number = 5) => api.post('/stats/run-classification', { mode: 'full', batch_size: batchSize }),
}
