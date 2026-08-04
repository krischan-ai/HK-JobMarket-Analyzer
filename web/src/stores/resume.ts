import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { resumeApi, ResumeResult } from '@/api/resume'
import { apiBaseURL } from '@/api/client'

function emptyResult(): ResumeResult {
  return {
    success: true,
    polish_suggestions: [],
    score: null,
    gap_analysis: null,
    matched_jobs: [],
    market_context: null,
    market_insights: null,
    target_role_understanding: null,
    match_advice: null,
    input_health: null,
    job_research: null,
    bullet_inventory: [],
    rerank_used: null,
  }
}

export const useResumeStore = defineStore('resume', () => {
  const resumeText = ref('')
  const jdText = ref('')
  const jdUrl = ref('')
  const targetRole = ref('')
  const targetRoleId = ref('')
  const targetMarket = ref('')
  const applicationStatus = ref('')
  const maxRetries = ref(1)
  const loading = ref(false)
  const streaming = ref(false)
  const stageMessage = ref('')
  const streamingText = ref('')  // 当前阶段模型实时输出的原始 token
  const uploading = ref(false)
  const resumeFileName = ref('')
  const result = ref<ResumeResult | null>(null)
  const error = ref('')
  const activeTab = ref('score')

  // 目标 JD 选填：仅简历必填，JD 留空时后端会用知识库相似岗位进行分析。
  const canSubmit = computed(() => resumeText.value.trim().length >= 50 && !loading.value)
  const knowledgeBaseMode = computed(() => jdText.value.trim().length < 30)

  async function polish() {
    loading.value = true
    error.value = ''
    try {
      result.value = await resumeApi.polish({
        resume_text: resumeText.value,
        jd_text: jdText.value,
        jd_url: jdUrl.value || undefined,
        target_role: targetRole.value || undefined,
        target_role_id: targetRoleId.value || undefined,
        target_market: targetMarket.value || undefined,
        application_status: applicationStatus.value || undefined,
        max_retries: maxRetries.value,
      })
      activeTab.value = result.value?.job_research ? 'research' : 'score'
    } catch (exc: any) {
      error.value = exc?.response?.data?.detail || exc?.message || '潤色失敗，請檢查 LLM 配置'
    } finally {
      loading.value = false
    }
  }

  function applyEvent(ev: any) {
    if (!result.value) result.value = emptyResult()
    const r = result.value
    switch (ev.stage) {
      case 'status':
        stageMessage.value = ev.message || ''
        streamingText.value = ''  // 进入新阶段，清空上一阶段的实时输出
        break
      case 'token':
        streamingText.value += ev.delta || ''
        break
      case 'input_health':
        r.input_health = ev.input_health || null
        break
      case 'matched_jobs':
        r.matched_jobs = ev.matched_jobs || []
        r.rerank_used = ev.rerank_used
        r.match_advice = ev.match_advice || null
        break
      case 'target_understanding':
        r.target_role_understanding = ev.target_role_understanding || null
        break
      case 'market_insights':
        r.market_insights = ev.market_insights || null
        r.market_context = ev.market_context || null
        break
      case 'job_research':
        r.job_research = ev.job_research || null
        activeTab.value = 'research'
        break
      case 'gap':
        r.gap_analysis = ev.gap_analysis || null
        break
      case 'polish':
        r.polish_suggestions = ev.polish_suggestions || []
        break
      case 'score':
        r.score = ev.score || null
        activeTab.value = 'score'
        break
      case 'interview_prep':
        r.bullet_inventory = ev.bullet_inventory || []
        break
      case 'done':
        if (ev.result) result.value = ev.result
        break
      case 'error':
        error.value = ev.error || '潤色失敗'
        break
    }
  }

  async function polishStream() {
    streaming.value = true
    loading.value = true
    error.value = ''
    stageMessage.value = '正在啟動…'
    streamingText.value = ''
    result.value = emptyResult()
    activeTab.value = 'gap'
    try {
      const resp = await fetch(`${apiBaseURL}/resume/polish-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: resumeText.value,
          jd_text: jdText.value || undefined,
          jd_url: jdUrl.value || undefined,
          target_role: targetRole.value || undefined,
          target_role_id: targetRoleId.value || undefined,
          target_market: targetMarket.value || undefined,
          application_status: applicationStatus.value || undefined,
          max_retries: maxRetries.value,
        }),
      })
      if (!resp.ok || !resp.body) {
        let detail = '潤色失敗，請檢查 LLM 配置'
        try {
          const j = await resp.json()
          detail = j.detail || detail
        } catch {
          // ignore non-JSON error body
        }
        throw new Error(detail)
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const frames = buffer.split('\n\n')
        buffer = frames.pop() || ''
        for (const frame of frames) {
          const line = frame.split('\n').find((l) => l.startsWith('data:'))
          if (!line) continue
          const payload = line.slice(5).trim()
          if (payload) applyEvent(JSON.parse(payload))
        }
      }
    } catch (e: any) {
      error.value = e?.message || '潤色失敗，請檢查 LLM 配置'
    } finally {
      streaming.value = false
      loading.value = false
      stageMessage.value = ''
      streamingText.value = ''
    }
  }

  async function extractPdf(file: File) {
    uploading.value = true
    error.value = ''
    try {
      const data = await resumeApi.extractPdf(file)
      resumeText.value = data.resume_text
      resumeFileName.value = file.name
      return true
    } catch (exc: any) {
      error.value = exc?.response?.data?.detail || exc?.message || 'PDF 解析失敗，請改用貼上文本'
      return false
    } finally {
      uploading.value = false
    }
  }

  function clear() {
    resumeText.value = ''
    jdText.value = ''
    jdUrl.value = ''
    targetRole.value = ''
    targetRoleId.value = ''
    targetMarket.value = ''
    applicationStatus.value = ''
    resumeFileName.value = ''
    result.value = null
    error.value = ''
    stageMessage.value = ''
    streamingText.value = ''
    activeTab.value = 'score'
  }

  return {
    resumeText,
    jdText,
    jdUrl,
    targetRole,
    targetRoleId,
    targetMarket,
    applicationStatus,
    maxRetries,
    loading,
    streaming,
    stageMessage,
    streamingText,
    uploading,
    resumeFileName,
    result,
    error,
    activeTab,
    canSubmit,
    knowledgeBaseMode,
    polish,
    polishStream,
    extractPdf,
    clear,
  }
})
