import api from './client'

export interface PostProcessConfigDTO {
  run_cleaning?: boolean
  run_extraction?: boolean
  run_classification?: boolean
  run_kb_import?: boolean
  run_vector_index?: boolean
  fail_on_error?: boolean
}

export interface CrawlerTaskDTO {
  task_id: string
  keywords: string[]
  sources: string[]
  status: string
  status_label: string
  progress: number
  total_jobs: number
  source_progress: Record<string, { total: number; collected: number }>
  created_at: string
  completed_at: string | null
  post_config: Record<string, boolean>
  post_phase: string
  post_phase_pct: number
  post_result: {
    cleaned_count?: number
    extracted_count?: number
    classified_count?: number
    db_inserted?: number
    vector_indexed?: number
    csv_exported?: number
    phase_timings?: Record<string, number>
    errors?: string[]
  } | null
}

export interface CrawlerTaskDetailDTO extends CrawlerTaskDTO {
  logs: Array<{ time: string; level: string; message: string }>
}

export interface CrawlerTaskListResponse {
  total: number
  items: CrawlerTaskDTO[]
}

export interface CrawlerSourcesResponse {
  sources: string[]
}

// 后处理阶段中英文映射
export const POST_PHASE_LABELS: Record<string, string> = {
  cleaning: '清洗',
  extraction: '技能提取',
  classification: '角色分類',
  kb_import: '知識庫導入',
  vector_index: '向量索引',
  done: '完成',
}

export const crawlerApi = {
  getSources: () => api.get<CrawlerSourcesResponse>('/crawler/sources'),

  createTask: (keywords: string[], sources: string[], postConfig?: PostProcessConfigDTO) =>
    api.post<CrawlerTaskDTO>('/crawler/tasks', { keywords, sources, post_config: postConfig || null }),

  listTasks: (status?: string) =>
    api.get<CrawlerTaskListResponse>('/crawler/tasks', { params: status ? { status } : {} }),

  getTask: (taskId: string) =>
    api.get<CrawlerTaskDetailDTO>(`/crawler/tasks/${taskId}`),

  startTask: (taskId: string) =>
    api.post<CrawlerTaskDTO>(`/crawler/tasks/${taskId}/start`),

  pauseTask: (taskId: string) =>
    api.post<CrawlerTaskDTO>(`/crawler/tasks/${taskId}/pause`),

  resumeTask: (taskId: string) =>
    api.post<CrawlerTaskDTO>(`/crawler/tasks/${taskId}/resume`),

  cancelTask: (taskId: string) =>
    api.post<CrawlerTaskDTO>(`/crawler/tasks/${taskId}/cancel`),

  deleteTask: (taskId: string) =>
    api.delete(`/crawler/tasks/${taskId}`),

  getResults: (taskId: string, page = 1, pageSize = 20) =>
    api.get(`/crawler/tasks/${taskId}/results`, { params: { page, page_size: pageSize } }),
}
