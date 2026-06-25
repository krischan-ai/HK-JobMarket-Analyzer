import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { GeneratedResumeResult, resumeGenerateApi } from '@/api/resumeGenerate'
import { apiBaseURL } from '@/api/client'

function emptyResult(): GeneratedResumeResult {
  return {
    success: false,
    generated_resume: null,
    markdown: '',
    target_job_profile: null,
    capability_matches: [],
    selected_experience_plan: null,
    selected_experience: [],
    claim_audit: [],
    quality_gate: null,
    similar_jobs: [],
    input_health: null,
    confidence: 'medium',
  }
}

export const useResumeGenerateStore = defineStore('resumeGenerate', () => {
  const resumeText = ref('')
  const targetRole = ref('')
  const targetRoleId = ref('')
  const targetMarket = ref('Hong Kong')
  const language = ref<'en' | 'zh-Hant' | 'zh-Hans'>('en')
  const style = ref<'professional' | 'technical' | 'management'>('professional')
  const narrativeAngle = ref('engineering')
  const topKJobs = ref(8)
  const loading = ref(false)
  const streaming = ref(false)
  const uploading = ref(false)
  const resumeFileName = ref('')
  const result = ref<GeneratedResumeResult | null>(null)
  const error = ref('')
  const activeTab = ref('resume')
  const stageMessage = ref('')
  const streamingText = ref('')
  const currentStep = ref('')

  const canSubmit = computed(() => resumeText.value.trim().length >= 10 && targetRole.value.trim().length >= 2 && !loading.value)

  function applyEvent(ev: any) {
    if (!result.value) result.value = emptyResult()
    const r = result.value
    switch (ev.stage) {
      case 'status':
        stageMessage.value = ev.message || ''
        currentStep.value = ev.step || ''
        streamingText.value = ''
        break
      case 'token':
        streamingText.value += ev.delta || ''
        break
      case 'input_health':
        r.input_health = ev.input_health || null
        activeTab.value = 'quality'
        break
      case 'profile':
        // resume_profile is not directly in the response, but target_job_profile uses it
        break
      case 'target_profile':
        r.target_job_profile = ev.target_job_profile || null
        r.similar_jobs = ev.target_job_profile?.similar_jobs || r.similar_jobs
        activeTab.value = 'profile'
        break
      case 'capability_matches':
        r.capability_matches = ev.capability_matches || []
        activeTab.value = 'match'
        break
      case 'selection_plan':
        r.selected_experience_plan = ev.selection_plan || null
        r.selected_experience = ev.selected_experience || []
        activeTab.value = 'selection'
        break
      case 'generated_resume':
        r.generated_resume = ev.generated_resume || null
        activeTab.value = 'resume'
        break
      case 'claim_audit':
        r.claim_audit = ev.claim_audit || []
        activeTab.value = 'audit'
        break
      case 'quality_gate':
        r.quality_gate = ev.quality_gate || null
        activeTab.value = 'quality'
        break
      case 'markdown':
        r.markdown = ev.markdown || ''
        activeTab.value = 'resume'
        break
      case 'done':
        if (ev.result) result.value = ev.result
        activeTab.value = ev.result?.markdown ? 'resume' : 'quality'
        break
      case 'error':
        error.value = ev.error || '生成失敗'
        break
    }
  }

  async function generateStream() {
    streaming.value = true
    loading.value = true
    error.value = ''
    stageMessage.value = '正在啟動…'
    streamingText.value = ''
    currentStep.value = ''
    result.value = emptyResult()
    activeTab.value = 'quality'
    try {
      const resp = await fetch(`${apiBaseURL}/resume/generate-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: resumeText.value,
          target_role: targetRole.value,
          target_role_id: targetRoleId.value || undefined,
          target_market: targetMarket.value || undefined,
          language: language.value,
          style: style.value,
          narrative_angle: narrativeAngle.value || undefined,
          top_k_jobs: topKJobs.value,
          auto_continue_without_confirmation: true,
        }),
      })
      if (!resp.ok || !resp.body) {
        let detail = '生成失敗，請檢查 LLM 配置'
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
      error.value = e?.message || '生成失敗，請檢查 LLM 配置'
    } finally {
      streaming.value = false
      loading.value = false
      stageMessage.value = ''
      streamingText.value = ''
      currentStep.value = ''
    }
  }

  async function generate() {
    await generateStream()
  }

  async function extractPdf(file: File) {
    uploading.value = true
    error.value = ''
    try {
      const data = await resumeGenerateApi.extractPdf(file)
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

  function downloadMarkdown() {
    if (!result.value?.markdown) return
    const blob = new Blob([result.value.markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `generated-resume-${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function copyMarkdown() {
    if (!result.value?.markdown) return
    await navigator.clipboard.writeText(result.value.markdown)
  }

  function clear() {
    resumeText.value = ''
    targetRole.value = ''
    targetRoleId.value = ''
    targetMarket.value = 'Hong Kong'
    language.value = 'en'
    style.value = 'professional'
    narrativeAngle.value = 'engineering'
    topKJobs.value = 8
    resumeFileName.value = ''
    result.value = null
    error.value = ''
    activeTab.value = 'resume'
    stageMessage.value = ''
    streamingText.value = ''
    currentStep.value = ''
  }

  return {
    resumeText,
    targetRole,
    targetRoleId,
    targetMarket,
    language,
    style,
    narrativeAngle,
    topKJobs,
    loading,
    streaming,
    uploading,
    resumeFileName,
    result,
    error,
    activeTab,
    stageMessage,
    streamingText,
    currentStep,
    canSubmit,
    generate,
    generateStream,
    extractPdf,
    downloadMarkdown,
    copyMarkdown,
    clear,
  }
})
