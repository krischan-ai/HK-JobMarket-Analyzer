import api from './client'

export interface PolishSection {
  section: string
  original: string
  suggested: string
  changes: string[]
  keywords_added: string[]
}

export interface ScoreReport {
  overall_score: number
  keyword_coverage: number
  experience_alignment: number
  skill_relevance: number
  language_quality: number
  suggestions: string[]
}

export interface ResumeResult {
  success: boolean
  polish_suggestions: PolishSection[]
  score: ScoreReport | null
  gap_analysis: Record<string, any> | null
  matched_jobs: Record<string, any>[]
  error?: string | null
}

export interface ResumePolishPayload {
  resume_text: string
  jd_text: string
  jd_url?: string
  target_role?: string
  max_retries?: number
}

export const resumeApi = {
  async polish(payload: ResumePolishPayload) {
    const { data } = await api.post<ResumeResult>('/resume/polish', payload)
    return data
  },
}
