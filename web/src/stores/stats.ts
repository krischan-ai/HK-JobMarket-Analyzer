import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import type { SkillFrequency, CategoryDistribution, SalaryDistribution, RoleDistribution, RoleSalaryStats, LLMClassificationStatus, ClassificationResult } from '@/types'

export const useStatsStore = defineStore('stats', () => {
  const topSkills = ref<SkillFrequency[]>([])
  const categories = ref<CategoryDistribution[]>([])
  const salaryByLocation = ref<SalaryDistribution[]>([])
  const roleDistribution = ref<RoleDistribution[]>([])
  const roleSalary = ref<RoleSalaryStats[]>([])
  const llmStatus = ref<LLMClassificationStatus | null>(null)
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

  async function runClassification(batchSize: number = 5) {
    classifying.value = true
    try {
      const { data } = await api.post<ClassificationResult>('/stats/run-classification', { mode: 'full', batch_size: batchSize })
      return data
    } finally {
      classifying.value = false
    }
  }

  return {
    topSkills, categories, salaryByLocation,
    roleDistribution, roleSalary, llmStatus, classifying, loading,
    fetchTopSkills, fetchCategories, fetchSalaryByLocation,
    fetchRoleDistribution, fetchRoleSalary, fetchLLMStatus, runClassification,
  }
})
