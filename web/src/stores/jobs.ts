import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import type { DashboardData, JobItem } from '@/types'

export const useJobsStore = defineStore('jobs', () => {
  const dashboard = ref<DashboardData | null>(null)
  const jobs = ref<JobItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(20)

  async function fetchDashboard() {
    loading.value = true
    try {
      const { data } = await api.get('/stats/dashboard')
      dashboard.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchJobs(params: Record<string, any> = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/jobs', { params: { page: currentPage.value, page_size: pageSize.value, ...params } })
      jobs.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  return { dashboard, jobs, total, loading, currentPage, pageSize, fetchDashboard, fetchJobs }
})
