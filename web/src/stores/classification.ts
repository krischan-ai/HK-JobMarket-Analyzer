import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '@/api'

export interface ClassifiedJob {
  job_id: string
  title: string
  company: string
  location: string
  source: string
  role_id: string
  role_name: string
  role_confidence: string
  salary_min: number
  salary_max: number
  skills: Array<{ name: string; category: string }>
  is_insurance_sales: boolean
  insurance_score: number
  llm_is_insurance: boolean
  llm_confidence: string
  llm_explanation: string
}

export interface InsuranceReviewItem {
  job_id: string
  title: string
  company: string
  is_insurance_sales: boolean
  insurance_score: number
  llm_is_insurance: boolean
  llm_confidence: string
  llm_explanation: string
}

export interface InsuranceReviewResult {
  success: boolean
  total: number
  insurance_confirmed: number
  duration_ms: number
  message: string
  items: InsuranceReviewItem[]
}

export interface ClassifyResult {
  success: boolean
  total: number
  classified: number
  duration_ms: number
  llm_mode: boolean
  message: string
  items: ClassifiedJob[]
}

export interface RoleDistItem {
  role_id: string
  role_name: string
  count: number
  percentage: number
}

export const useClassificationStore = defineStore('classification', () => {
  const running = ref(false)
  const progress = ref(0)
  const total = ref(0)
  const classified = ref(0)
  const duration = ref(0)
  const llmMode = ref(false)
  const message = ref('')
  const results = ref<ClassifiedJob[]>([])
  const distribution = ref<RoleDistItem[]>([])
  const llmAvailable = ref(false)
  const coverageRate = ref(0)

  // filter/stats state
  const roleFilter = ref('')
  const reviewing = ref(false)

  const filteredResults = computed(() => {
    let items = results.value
    if (roleFilter.value) {
      items = items.filter((j) => j.role_id === roleFilter.value)
    }
    return items
  })

  const roleStats = computed(() => {
    const map: Record<string, { role_id: string; role_name: string; count: number }> = {}
    for (const j of results.value) {
      const id = j.role_id
      if (!map[id]) map[id] = { role_id: id, role_name: j.role_name, count: 0 }
      map[id].count++
    }
    return Object.values(map).sort((a, b) => b.count - a.count)
  })

  const uniqueSkills = computed(() => {
    const set = new Set<string>()
    for (const j of results.value) {
      for (const s of j.skills) {
        set.add(s.name)
      }
    }
    return Array.from(set).sort()
  })

  const insuranceCount = computed(() =>
    results.value.filter((j) => j.is_insurance_sales).length
  )

  const llmInsuranceCount = computed(() =>
    results.value.filter((j) => j.llm_is_insurance).length
  )

  async function reviewInsurance() {
    const suspectIds = results.value
      .filter((j) => j.is_insurance_sales)
      .map((j) => j.job_id)
    if (!suspectIds.length) {
      message.value = '沒有需要復審的疑似保險崗位'
      return
    }

    reviewing.value = true
    message.value = `正在 LLM 復審 ${suspectIds.length} 個疑似保險崗位...`

    try {
      const { data } = await api.post<InsuranceReviewResult>(
        '/stats/review-insurance',
        { job_ids: suspectIds },
        { timeout: 300000 }
      )

      // 将复审结果合并到 results
      const reviewMap = new Map(data.items.map((r: InsuranceReviewItem) => [r.job_id, r]))
      for (const j of results.value) {
        const review = reviewMap.get(j.job_id)
        if (review) {
          j.llm_is_insurance = review.llm_is_insurance
          j.llm_confidence = review.llm_confidence
          j.llm_explanation = review.llm_explanation
        }
      }
      message.value = data.message
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      message.value = err?.response?.data?.detail || err?.message || 'LLM 復審失敗'
    } finally {
      reviewing.value = false
    }
  }

  async function fetchStatus() {
    try {
      const { data } = await api.get('/stats/llm-status')
      llmAvailable.value = data.llm_available
      coverageRate.value = data.coverage_rate
    } catch {
      llmAvailable.value = false
    }
  }

  async function fetchDistribution() {
    try {
      const { data } = await api.get('/stats/role-distribution')
      distribution.value = data
    } catch {
      distribution.value = []
    }
  }

  async function runClassify(batchSize = 5) {
    running.value = true
    progress.value = 0
    total.value = 0
    classified.value = 0
    results.value = []
    message.value = '正在初始化分類...'

    try {
      const { data } = await api.post<ClassifyResult>('/stats/classify-jobs', {
        mode: 'full',
        batch_size: batchSize,
      }, { timeout: 300000 })

      results.value = data.items || []
      total.value = data.total
      classified.value = data.classified
      duration.value = data.duration_ms
      llmMode.value = data.llm_mode
      progress.value = 100
      message.value = data.message
      await fetchDistribution()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      message.value = err?.response?.data?.detail || err?.message || '分類失敗'
    } finally {
      running.value = false
    }
  }

  // Poll progress during long classification
  async function runWithPoll(batchSize = 5) {
    running.value = true
    progress.value = 0
    total.value = 0
    results.value = []
    message.value = '正在初始化...'

    try {
      const { data } = await api.post<ClassifyResult>('/stats/classify-jobs', {
        mode: 'full',
        batch_size: batchSize,
      }, { timeout: 600000 })

      results.value = data.items || []
      total.value = data.total
      classified.value = data.classified
      duration.value = data.duration_ms
      llmMode.value = data.llm_mode
      progress.value = 100
      message.value = data.message

      // Refresh distribution
      const distResp = await api.get('/stats/role-distribution')
      distribution.value = distResp.data
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      message.value = err?.response?.data?.detail || err?.message || '分類失敗'
    } finally {
      running.value = false
    }
  }

  return {
    running, progress, total, classified, duration, llmMode, message,
    results, filteredResults, distribution, roleStats, uniqueSkills,
    llmAvailable, coverageRate, roleFilter,
    insuranceCount, llmInsuranceCount,
    reviewing, reviewInsurance,
    fetchStatus, fetchDistribution, runClassify, runWithPoll,
  }
})
