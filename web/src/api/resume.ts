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
  overall_comment: string
  dimension_reasons: Record<string, string>
  suggestions: string[]
}

export interface SkillStat {
  skill: string
  count: number
}

export interface InputHealth {
  status: string
  target_role?: string | null
  target_role_id?: string | null
  target_market?: string | null
  jd_status: string
  resume_status: string
  application_status: string
  assumptions: string[]
  gaps: string[]
  blocking_questions: string[]
}

export interface JobResearchReport {
  target_role?: string | null
  source: string
  confidence: string
  sample_count: number
  core_capabilities: string[]
  high_frequency_skills: SkillStat[]
  tech_stack_themes: Array<{ theme: string; items: string[]; evidence?: string[] }>
  other_competencies: string[]
  common_titles: string[]
  common_responsibilities: string[]
  hidden_requirements: string[]
  similar_jobs: Record<string, any>[]
  resume_positioning_advice: string[]
  source_coverage_note: string
}

export interface BulletInventoryItem {
  bullet_id: string
  final_text: string
  target_capability: string
  evidence_source: string
  evidence_confidence: string
  talk_track_30s: string
  follow_up_questions: string[]
  risk_notes: string[]
  fallback_answer: string
}

export interface ResumeResult {
  success: boolean
  polish_suggestions: PolishSection[]
  score: ScoreReport | null
  gap_analysis: Record<string, any> | null
  matched_jobs: Record<string, any>[]
  market_context: Record<string, any> | null
  market_insights: Record<string, any> | null
  target_role_understanding?: Record<string, any> | null
  match_advice?: { summary?: string; suggestions?: string[] } | null
  input_health: InputHealth | null
  job_research: JobResearchReport | null
  bullet_inventory: BulletInventoryItem[]
  rerank_used?: boolean | null
  error?: string | null
}

export interface PdfExtractResult {
  success: boolean
  resume_text: string
  char_count: number
  error?: string | null
}

export interface ResumePolishPayload {
  resume_text: string
  jd_text?: string
  jd_url?: string
  target_role?: string
  target_role_id?: string
  target_market?: string
  application_status?: string
  max_retries?: number
}

export const resumeApi = {
  async polish(payload: ResumePolishPayload) {
    const { data } = await api.post<ResumeResult>('/resume/polish', payload)
    return data
  },

  async extractPdf(file: File) {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<PdfExtractResult>('/resume/extract-pdf', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
}
