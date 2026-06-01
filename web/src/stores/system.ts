import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useSystemStore = defineStore('system', () => {
  const healthy = ref(false)
  const dataCount = ref(0)
  const version = ref('')

  async function checkHealth() {
    try {
      const { data } = await api.get('/system/health')
      healthy.value = data.status === 'healthy'
      dataCount.value = data.data_count
      version.value = data.version
    } catch {
      healthy.value = false
    }
  }

  return { healthy, dataCount, version, checkHealth }
})
