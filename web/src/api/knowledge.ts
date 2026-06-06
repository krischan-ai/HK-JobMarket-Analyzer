import api from './client'

export interface SemanticSearchResult {
  doc_id: string
  job_id: string
  title: string
  company: string
  location: string
  source: string
  score: number
  snippet: string
}

export interface SemanticSearchResponse {
  available: boolean
  results: SemanticSearchResult[]
  query: string
  message?: string
}

export interface VectorStatusResponse {
  available: boolean
  doc_count: number
  persist_path: string
}

export const knowledgeApi = {
  search: (kw: string) => api.get('/knowledge/search', { params: { kw } }),
  skillFrequency: (topN: number = 15) => api.get('/knowledge/skill-frequency', { params: { top_n: topN } }),
  versions: () => api.get('/knowledge/versions'),

  // Vector semantic search
  semanticSearch: (q: string) => api.get<SemanticSearchResponse>('/knowledge/semantic-search', { params: { q } }),
  vectorStatus: () => api.get<VectorStatusResponse>('/knowledge/vector-status'),
  vectorRebuild: () => api.post<{ success: boolean; doc_count?: number; message?: string }>('/knowledge/vector-rebuild'),
  vectorClear: () => api.delete<{ success: boolean; doc_count: number }>('/knowledge/vector-clear'),
}
