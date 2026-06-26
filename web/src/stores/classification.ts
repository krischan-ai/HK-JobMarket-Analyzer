import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '@/api'
import type { SoftSkillTags } from '@/types'

export interface ClassifiedJob {
  job_id: string
  title: string
  company: string
  location: string
  source: string
  industry_category?: string
  role_id: string
  role_name: string
  role_confidence: string
  salary_min: number
  salary_max: number
  skills: Array<{ name: string; category: string }>
  soft_skills?: SoftSkillTags
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
  const useLLM = ref(true)  // 用户选择是否使用 LLM
  const message = ref('')
  const results = ref<ClassifiedJob[]>([])
  const distribution = ref<RoleDistItem[]>([])
  const llmAvailable = ref(false)
  const coverageRate = ref(0)
  const lastClassifiedAt = ref<string | null>(null)
  let _pollTimer: ReturnType<typeof setInterval> | null = null

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
      const err = e as { response?: { status?: number; data?: { detail?: string } }; message?: string }
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

  // 启动分类 + 轮询进度（POST 立即返回，后端后台执行）
  async function startClassify(batchSize = 5) {
    running.value = true
    progress.value = 0
    total.value = 0
    classified.value = 0
    duration.value = 0
    results.value = []
    message.value = '正在啟動分類任務...'

    try {
      const { data } = await api.post('/stats/classify-jobs', {
        mode: 'full',
        batch_size: batchSize,
        use_llm: useLLM.value,
      })

      total.value = data.total || 0
      message.value = '分類中...'
      _startPolling()
    } catch (e: unknown) {
      const err = e as { response?: { status?: number; data?: { detail?: string } }; message?: string }
      if (err?.response?.status === 409) {
        message.value = '已有任務正在運行，正在恢復監聽...'
        _startPolling()
      } else {
        message.value = err?.response?.data?.detail || err?.message || '啟動失敗'
        running.value = false
      }
    }
  }

  // 页面挂载时调用：恢复进度监听 / 加载已有结果
  async function resumeOnMount() {
    _stopPoll()
    try {
      const { data } = await api.get('/stats/classify-progress')
      if (data.running) {
        // 后台有任务在跑 → 恢复进度显示并开始轮询
        running.value = true
        total.value = data.total || 0
        progress.value = data.progress || 0
        message.value = data.message || '分類中...'
        llmMode.value = data.llm_mode || false
        _startPolling()
      } else if (data.results && data.results.length > 0) {
        // 任务已完成 → 加载缓存结果
        results.value = data.results
        total.value = data.total || data.results.length
        progress.value = 100
        classified.value = data.classified || data.results.length
        duration.value = data.duration_ms || 0
        llmMode.value = data.llm_mode || false
        lastClassifiedAt.value = data.last_classified_at || null
        message.value = data.message || '分類完成'
        running.value = false
      } else {
        // 无历史结果
        running.value = false
      }
    } catch {
      running.value = false
    }
  }

  function _startPolling() {
    _stopPoll()
    _pollTimer = setInterval(async () => {
      try {
        const { data } = await api.get('/stats/classify-progress')
        progress.value = data.progress || 0
        total.value = data.total || total.value
        message.value = data.message || ''
        llmMode.value = data.llm_mode || false

        if (!data.running) {
          _stopPoll()
          running.value = false
          // 任务完成 → 加载结果
          if (data.results && data.results.length > 0) {
            results.value = data.results
            classified.value = data.classified || data.results.length
            duration.value = data.duration_ms || 0
            lastClassifiedAt.value = data.last_classified_at || null
            await fetchDistribution()
          } else if (data.last_classified_at) {
            lastClassifiedAt.value = data.last_classified_at
          }
        }
      } catch { /* ignore poll errors */ }
    }, 1500)
  }

  function _stopPoll() {
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  return {
    running, progress, total, classified, duration, llmMode, useLLM, message,
    results, filteredResults, distribution, roleStats, uniqueSkills,
    llmAvailable, coverageRate, roleFilter, lastClassifiedAt,
    insuranceCount, llmInsuranceCount,
    reviewing, reviewInsurance,
    fetchStatus, fetchDistribution, startClassify, resumeOnMount,
  }
})
