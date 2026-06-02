import api from './client'

export const uploadApi = {
  uploadFile: (file: File, sourceTag: string = 'user_upload') => {
    const form = new FormData()
    form.append('file', file)
    form.append('source_tag', sourceTag)
    form.append('run_cleaning', 'true')
    form.append('run_extraction', 'true')
    return api.post('/upload/file', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
