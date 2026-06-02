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
  salary_currency?: string
  url?: string
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
