export interface JobItem {
  job_id: string
  title: string
  company: string
  location: string
  salary_min?: number
  salary_max?: number
  source: string
  skills?: Record<string, string[]>
  jd_raw?: string
  jd_text?: string
  import_time?: string
  salary_currency?: string
  url?: string
  posted_at?: string
  employment_type?: string
  industry_category?: string
  application_volume?: string
  employer_questions?: string[]
  is_insurance_sales?: boolean
  insurance_score?: number | null
  insurance_reasons?: string[]
  work_mode?: string
  posted_days_ago?: number | null
  company_size?: string
  education_required?: string
  languages_required?: string[]
  tech_stack?: string[]
  soft_skills?: SoftSkillTags
  tag_profile?: TagProfile
  job_type?: string
}

export interface SoftSkillTags {
  education: string[]
  language: string[]
  soft_skill: string[]
  domain_knowledge?: string[]
  certification?: string[]
  business_skill?: string[]
}

export type RequirementLevel = 'required' | 'preferred' | 'example' | 'inferred'

export interface StructuredTag {
  name: string
  category: string
  requirement_level: RequirementLevel
  source?: string
  confidence: number
  evidence?: string
}

export interface TagProfile {
  technical: StructuredTag[]
  non_technical: StructuredTag[]
}

export interface JobListResponse {
  total: number
  page: number
  page_size: number
  items: JobItem[]
}

export interface StatsOverview {
  total_jobs: number
  total_companies: number
  avg_salary: number
  min_salary: number
  max_salary: number
  total_skills: number
  source_count: number
  location_count: number
}

export interface SkillFrequency {
  skill: string
  count: number
  category?: string
}

export interface CategoryDistribution {
  category: string
  count: number
}

export interface SalaryDistribution {
  location: string
  min: number
  max: number
  avg: number
  count: number
}

export interface SourceDistribution {
  source: string
  count: number
}

export interface LocationDistribution {
  location: string
  count: number
}

export interface DashboardData {
  overview: StatsOverview
  top_skills: SkillFrequency[]
  category_distribution: CategoryDistribution[]
  salary_by_location: SalaryDistribution[]
  source_distribution: SourceDistribution[]
}

export interface UploadResult {
  total: number
  success: number
  skipped: number
  new_records: number
  updated_records: number
  errors: string[]
  duration_ms: number
}

export interface LocationItem {
  name: string
  count: number
}

export interface RoleDistribution {
  role_id: string
  role_name: string
  count: number
  percentage: number
}

export interface RoleSalaryStats {
  role_id: string
  role_name: string
  salary_avg: number
  salary_min: number
  salary_max: number
  count: number
}

export interface LLMClassificationStatus {
  total_jobs: number
  classified: number
  coverage_rate: number
  last_analysis: string | null
  llm_available: boolean
}

export interface ClassificationResult {
  success: boolean
  total: number
  classified: number
  duration_ms: number
  message: string
}

export type ClassifiedSoftSkills = SoftSkillTags

export interface TechTrendSection {
  key: string
  title: string
  summary: string
  evidence?: Array<string | Record<string, unknown>>
}

export interface TechTrendAnalysis {
  llm_used: boolean
  from_cache?: boolean
  analysis_status?: 'cached' | 'completed' | 'fallback' | string
  warning?: string
  sections: TechTrendSection[]
  context?: Record<string, unknown>
}

export type SalaryAnalysis = TechTrendAnalysis
