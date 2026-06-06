import { defineStore } from 'pinia'
import { ref } from 'vue'
import { crawlerApi } from '@/api/crawler'
import type { CrawlerTaskDTO, CrawlerTaskDetailDTO, PostProcessConfigDTO } from '@/api/crawler'

// 轮询应停止的终态
const TERMINAL_STATUSES = ['processed', 'processing_failed', 'completed', 'failed', 'cancelled']

export const useCrawlerStore = defineStore('crawler', () => {
  const tasks = ref<CrawlerTaskDTO[]>([])
  const currentTask = ref<CrawlerTaskDetailDTO | null>(null)
  const availableSources = ref<string[]>([])
  const loading = ref(false)
  const polling = ref(false)

  let _pollTimer: ReturnType<typeof setInterval> | null = null

  async function fetchSources() {
    const { data } = await crawlerApi.getSources()
    availableSources.value = data.sources
  }

  async function fetchTasks(status?: string) {
    loading.value = true
    try {
      const { data } = await crawlerApi.listTasks(status)
      tasks.value = data.items
    } finally {
      loading.value = false
    }
  }

  async function createTask(keywords: string[], sources: string[], postConfig?: PostProcessConfigDTO) {
    const { data } = await crawlerApi.createTask(keywords, sources, postConfig)
    tasks.value.unshift(data)
    return data
  }

  async function fetchTaskDetail(taskId: string) {
    const { data } = await crawlerApi.getTask(taskId)
    currentTask.value = data
    return data
  }

  async function startTask(taskId: string) {
    await crawlerApi.startTask(taskId)
    startPolling(taskId)
  }

  async function pauseTask(taskId: string) {
    await crawlerApi.pauseTask(taskId)
    await fetchTaskDetail(taskId)
  }

  async function resumeTask(taskId: string) {
    await crawlerApi.resumeTask(taskId)
    startPolling(taskId)
  }

  async function cancelTask(taskId: string) {
    await crawlerApi.cancelTask(taskId)
    stopPolling()
    await fetchTaskDetail(taskId)
  }

  async function deleteTask(taskId: string) {
    await crawlerApi.deleteTask(taskId)
    tasks.value = tasks.value.filter((t) => t.task_id !== taskId)
    if (currentTask.value?.task_id === taskId) {
      currentTask.value = null
    }
  }

  function startPolling(taskId: string) {
    stopPolling()
    polling.value = true
    _pollTimer = setInterval(async () => {
      try {
        await fetchTaskDetail(taskId)
        const t = currentTask.value
        if (t && TERMINAL_STATUSES.includes(t.status)) {
          stopPolling()
          await fetchTasks()
        }
      } catch {
        stopPolling()
      }
    }, 2000)
  }

  function stopPolling() {
    polling.value = false
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  return {
    tasks,
    currentTask,
    availableSources,
    loading,
    polling,
    fetchSources,
    fetchTasks,
    createTask,
    fetchTaskDetail,
    startTask,
    pauseTask,
    resumeTask,
    cancelTask,
    deleteTask,
    startPolling,
    stopPolling,
  }
})
