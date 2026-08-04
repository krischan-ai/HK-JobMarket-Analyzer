import api from './client'

export interface GenerateInputHealth {
  status: string
  resume_status: string
  target_status: string
  assumptions: string[]
  gaps: string[]
  blocking_questions: string[]
}

export interface SkillStat {
  skill: string
  count: number
}

export interface TargetJobProfile {
  target_role: string
  source: string
  confidence: string
  sample_count: number
  core_capabilities: string[]
  high_frequency_skills: SkillStat[]
  tech_stack: Array<{ category: string; items: string[] }>
  common_titles: string[]
  common_responsibilities: string[]
  hidden_requirements: string[]
  similar_jobs: Record<string, any>[]
  source_coverage_note: string
}

export interface CapabilityMatch {
  capability: string
  job_basis: string
  matched_sources: string[]
  evidence_strength: string
  resume_angle: string
  risk_note: string
}

export interface SelectedExperience {
  source_type: string
  source_id: string
  source_title: string
  target_capability: string
  evidence_text: string
  selection_reason: string
  evidence_confidence: string
}

export interface SelectedExperiencePlan {
  selected: SelectedExperience[]
  excluded: Array<Record<string, string>>
  selection_summary: string
  user_confirmation_required: string[]
}

export interface ClaimEvidence {
  claim: string
  claim_type: string
  source: string
  confidence: string
  action: string
  reason: string
  suggested_revision: string
}

export interface QualityGateResult {
  status: string
  p0_violations: string[]
  p1_gaps: string[]
  suggested_fixes: string[]
}

export interface GeneratedResumeResult {
  success: boolean
  generated_resume: Record<string, any> | null
  markdown: string
  target_job_profile: TargetJobProfile | null
  capability_matches: CapabilityMatch[]
  selected_experience_plan: SelectedExperiencePlan | null
  selected_experience: SelectedExperience[]
  claim_audit: ClaimEvidence[]
  quality_gate: QualityGateResult | null
  similar_jobs: Record<string, any>[]
  input_health: GenerateInputHealth | null
  confidence: string
  error?: string | null
}

export interface ResumeGeneratePayload {
  resume_text: string
  target_role: string
  target_role_id?: string
  target_market?: string
  language?: 'en' | 'zh-Hant' | 'zh-Hans'
  style?: 'professional' | 'technical' | 'management'
  narrative_angle?: string
  top_k_jobs?: number
  profile_context?: Record<string, any>
  project_context?: Array<Record<string, any>>
  auto_continue_without_confirmation?: boolean
}

export interface PdfExtractResult {
  success: boolean
  resume_text: string
  char_count: number
  error?: string | null
}

export const resumeGenerateApi = {
  async generate(payload: ResumeGeneratePayload) {
    const { data } = await api.post<GeneratedResumeResult>('/resume/generate', payload)
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
