import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { resumeApi, ResumeResult } from '@/api/resume'

export const useResumeStore = defineStore('resume', () => {
  const resumeText = ref('')
  const jdText = ref('')
  const jdUrl = ref('')
  const targetRole = ref('')
  const maxRetries = ref(1)
  const loading = ref(false)
  const result = ref<ResumeResult | null>(null)
  const error = ref('')
  const activeTab = ref('score')

  const canSubmit = computed(() => resumeText.value.trim().length >= 50 && jdText.value.trim().length >= 50 && !loading.value)

  async function polish() {
    loading.value = true
    error.value = ''
    try {
      result.value = await resumeApi.polish({
        resume_text: resumeText.value,
        jd_text: jdText.value,
        jd_url: jdUrl.value || undefined,
        target_role: targetRole.value || undefined,
        max_retries: maxRetries.value,
      })
      activeTab.value = 'score'
    } catch (exc: any) {
      error.value = exc?.response?.data?.detail || exc?.message || '潤色失敗，請檢查 LLM 配置'
    } finally {
      loading.value = false
    }
  }

  function clear() {
    resumeText.value = ''
    jdText.value = ''
    jdUrl.value = ''
    targetRole.value = ''
    result.value = null
    error.value = ''
    activeTab.value = 'score'
  }

  return {
    resumeText,
    jdText,
    jdUrl,
    targetRole,
    maxRetries,
    loading,
    result,
    error,
    activeTab,
    canSubmit,
    polish,
    clear,
  }
})
