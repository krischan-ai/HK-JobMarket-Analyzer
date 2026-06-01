import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface LLMConfigDTO {
  configured: boolean
  base_url: string
  model: string
  api_key_set: boolean
}

export interface TestResult {
  success: boolean
  message: string
  latency_ms?: number
}

export const useLLMStore = defineStore('llm', () => {
  const configured = ref(false)
  const baseUrl = ref('https://api.deepseek.com/v1')
  const model = ref('deepseek-chat')
  const apiKeySet = ref(false)
  const testing = ref(false)
  const saving = ref(false)

  async function fetchStatus() {
    try {
      const { data } = await api.get<LLMConfigDTO>('/llm/config')
      configured.value = data.configured
      baseUrl.value = data.base_url
      model.value = data.model
      apiKeySet.value = data.api_key_set
    } catch {
      configured.value = false
    }
  }

  async function saveConfig(config: { api_key?: string; base_url?: string; model?: string; timeout?: number }) {
    saving.value = true
    try {
      const { data } = await api.put<LLMConfigDTO>('/llm/config', config)
      configured.value = data.configured
      baseUrl.value = data.base_url
      model.value = data.model
      apiKeySet.value = data.api_key_set
    } finally {
      saving.value = false
    }
  }

  async function clearConfig() {
    saving.value = true
    try {
      await api.delete('/llm/config')
      configured.value = false
      apiKeySet.value = false
    } finally {
      saving.value = false
    }
  }

  async function testConnection(): Promise<TestResult> {
    testing.value = true
    try {
      const { data } = await api.post<TestResult>('/llm/test')
      return data
    } finally {
      testing.value = false
    }
  }

  return { configured, baseUrl, model, apiKeySet, testing, saving, fetchStatus, saveConfig, clearConfig, testConnection }
})
