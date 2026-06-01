import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import type { UploadResult } from '@/types'

export const useUploadStore = defineStore('upload', () => {
  const uploading = ref(false)
  const result = ref<UploadResult | null>(null)

  async function uploadFile(file: File, sourceTag: string = 'user_upload') {
    uploading.value = true
    const form = new FormData()
    form.append('file', file)
    form.append('source_tag', sourceTag)
    form.append('run_cleaning', 'true')
    form.append('run_extraction', 'true')
    try {
      const { data } = await api.post('/upload/file', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      result.value = data
    } finally {
      uploading.value = false
    }
  }

  return { uploading, result, uploadFile }
})
