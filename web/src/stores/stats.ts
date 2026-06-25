import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import type { SkillFrequency, CategoryDistribution, SalaryDistribution, RoleDistribution, RoleSalaryStats, LLMClassificationStatus, ClassificationResult, TechTrendAnalysis, SalaryAnalysis } from '@/types'

export const useStatsStore = defineStore('stats', () => {
  const topSkills = ref<SkillFrequency[]>([])
  const categories = ref<CategoryDistribution[]>([])
  const salaryByLocation = ref<SalaryDistribution[]>([])
  const roleDistribution = ref<RoleDistribution[]>([])
  const roleSalary = ref<RoleSalaryStats[]>([])
  const llmStatus = ref<LLMClassificationStatus | null>(null)
  const techTrendAnalysis = ref<TechTrendAnalysis | null>(null)
  const techTrendLoading = ref(false)
  const techTrendError = ref('')
  const salaryAnalysis = ref<SalaryAnalysis | null>(null)
  const salaryAnalysisLoading = ref(false)
  const salaryAnalysisError = ref('')
  const classifying = ref(false)
  const loading = ref(false)

  async function fetchTopSkills(n: number = 15) {
    const { data } = await api.get('/stats/top-skills', { params: { top_n: n } })
    topSkills.value = data
  }

  async function fetchCategories() {
    const { data } = await api.get('/stats/categories')
    categories.value = data
  }

  async function fetchSalaryByLocation() {
    const { data } = await api.get('/stats/salary-by-location')
    salaryByLocation.value = data
  }

  async function fetchRoleDistribution() {
    try {
      const { data } = await api.get('/stats/role-distribution')
      roleDistribution.value = data
    } catch {
      roleDistribution.value = []
    }
  }

  async function fetchRoleSalary() {
    try {
      const { data } = await api.get('/stats/role-salary')
      roleSalary.value = data
    } catch {
      roleSalary.value = []
    }
  }

  async function fetchLLMStatus() {
    try {
      const { data } = await api.get<LLMClassificationStatus>('/stats/llm-status')
      llmStatus.value = data
    } catch {
      llmStatus.value = null
    }
  }

  async function fetchTechTrendAnalysis(refresh = false) {
    if (!refresh && techTrendAnalysis.value) {
      return techTrendAnalysis.value
    }
    techTrendLoading.value = true
    techTrendError.value = ''
    try {
      const { data } = await api.get<TechTrendAnalysis>('/stats/tech-trend-analysis', { params: { refresh } })
      techTrendAnalysis.value = data
      return data
    } catch (error: any) {
      techTrendAnalysis.value = null
      techTrendError.value = error?.response?.data?.detail || '技术趋势分析生成失败'
      throw error
    } finally {
      techTrendLoading.value = false
    }
  }

  async function fetchSalaryAnalysis(refresh = false) {
    if (!refresh && salaryAnalysis.value) {
      return salaryAnalysis.value
    }
    salaryAnalysisLoading.value = true
    salaryAnalysisError.value = ''
    try {
      const { data } = await api.get<SalaryAnalysis>('/stats/salary-analysis', { params: { refresh } })
      salaryAnalysis.value = data
      return data
    } catch (error: any) {
      salaryAnalysis.value = null
      salaryAnalysisError.value = error?.response?.data?.detail || '薪资智能分析生成失败'
      throw error
    } finally {
      salaryAnalysisLoading.value = false
    }
  }

  async function runClassification(batchSize: number = 5) {
    classifying.value = true
    try {
      const { data } = await api.post<ClassificationResult>('/stats/run-classification', { mode: 'full', batch_size: batchSize }, { timeout: 600000 })
      return data
    } finally {
      classifying.value = false
    }
  }

  return {
    topSkills, categories, salaryByLocation,
    roleDistribution, roleSalary, llmStatus,
    techTrendAnalysis, techTrendLoading, techTrendError,
    salaryAnalysis, salaryAnalysisLoading, salaryAnalysisError,
    classifying, loading,
    fetchTopSkills, fetchCategories, fetchSalaryByLocation,
    fetchRoleDistribution, fetchRoleSalary, fetchLLMStatus, fetchTechTrendAnalysis, fetchSalaryAnalysis, runClassification,
  }
})
