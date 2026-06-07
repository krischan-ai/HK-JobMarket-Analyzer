import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import api from '@/api'
import type { JobItem } from '@/types'

export interface JobFilters {
  keyword: string
  source: string
  location: string
  salaryMin: number | null
  salaryMax: number | null
}

export const useJobBrowseStore = defineStore('jobBrowse', () => {
  const jobs = ref<JobItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const selectedJob = ref<JobItem | null>(null)

  const filters = ref<JobFilters>({
    keyword: '',
    source: '',
    location: '',
    salaryMin: null,
    salaryMax: null,
  })

  const sources = ref<string[]>([])
  const locations = ref<{ name: string; count: number }[]>([])

  const hasActiveFilters = computed(() => {
    return !!(
      filters.value.keyword ||
      filters.value.source ||
      filters.value.location ||
      filters.value.salaryMin !== null ||
      filters.value.salaryMax !== null
    )
  })

  async function fetchJobs() {
    loading.value = true
    try {
      const params: Record<string, any> = {
        page: currentPage.value,
        page_size: pageSize.value,
      }
      if (filters.value.keyword) params.keyword = filters.value.keyword
      if (filters.value.source) params.source = filters.value.source
      if (filters.value.location) params.location = filters.value.location
      if (filters.value.salaryMin !== null) params.salary_min = filters.value.salaryMin
      if (filters.value.salaryMax !== null) params.salary_max = filters.value.salaryMax

      const { data } = await api.get('/jobs', { params })
      jobs.value = data.items
      total.value = data.total

      // 清除选中状态如果当前选中岗位不在列表中
      if (selectedJob.value && !jobs.value.find(j => j.job_id === selectedJob.value!.job_id)) {
        selectedJob.value = null
      }
      // 如果没有选中则默认选第一个
      if (!selectedJob.value && jobs.value.length > 0) {
        selectedJob.value = jobs.value[0]
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchSources() {
    try {
      const { data } = await api.get('/jobs/sources')
      sources.value = data
    } catch {
      sources.value = []
    }
  }

  async function fetchLocations() {
    try {
      const { data } = await api.get('/jobs/locations')
      locations.value = data
    } catch {
      locations.value = []
    }
  }

  function selectJob(job: JobItem) {
    selectedJob.value = job
  }

  function setFilter<K extends keyof JobFilters>(key: K, value: JobFilters[K]) {
    filters.value[key] = value
  }

  function resetFilters() {
    filters.value = { keyword: '', source: '', location: '', salaryMin: null, salaryMax: null }
  }

  function goToPage(page: number, size?: number) {
    currentPage.value = page
    if (size) pageSize.value = size
    fetchJobs()
  }

  function search() {
    currentPage.value = 1
    fetchJobs()
  }

  return {
    jobs, total, loading, currentPage, pageSize, selectedJob,
    filters, sources, locations, hasActiveFilters,
    fetchJobs, fetchSources, fetchLocations,
    selectJob, setFilter, resetFilters, goToPage, search,
  }
})
