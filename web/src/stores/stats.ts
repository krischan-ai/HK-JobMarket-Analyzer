import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import type { SkillFrequency, CategoryDistribution, SalaryDistribution } from '@/types'

export const useStatsStore = defineStore('stats', () => {
  const topSkills = ref<SkillFrequency[]>([])
  const categories = ref<CategoryDistribution[]>([])
  const salaryByLocation = ref<SalaryDistribution[]>([])
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

  return { topSkills, categories, salaryByLocation, loading, fetchTopSkills, fetchCategories, fetchSalaryByLocation }
})
