<template>
  <div>
    <h2 style="margin-top: 0">⚙️ 系統設置</h2>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="系統信息" name="system">
        <el-card>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="API 狀態">
              <el-tag :type="systemStore.healthy ? 'success' : 'danger'">{{ systemStore.healthy ? '正常' : '離線' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="數據總量">{{ systemStore.dataCount }} 條</el-descriptions-item>
            <el-descriptions-item label="版本">{{ systemStore.version }}</el-descriptions-item>
            <el-descriptions-item label="API 地址">http://localhost:8000</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="LLM 配置" name="llm">
        <el-card>
          <el-alert
            :title="llmStore.configured ? 'LLM 已配置' : 'LLM 未配置 — 請填入 API 資訊後保存'"
            :type="llmStore.configured ? 'success' : 'warning'"
            :closable="false"
            style="margin-bottom: 16px"
          />

          <el-form :model="form" label-width="120px" style="max-width: 600px">
            <el-form-item label="API Key" required>
              <el-input
                v-model="form.api_key"
                type="password"
                show-password
                :placeholder="llmStore.apiKeySet ? '已儲存（輸入新值可覆蓋）' : 'sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'"
                @input="formDirty = true"
              >
                <template #prefix><el-icon><Lock /></el-icon></template>
              </el-input>
            </el-form-item>

            <el-form-item label="Base URL" required>
              <el-input
                v-model="form.base_url"
                placeholder="https://api.deepseek.com/v1"
                @input="formDirty = true"
              >
                <template #prefix><el-icon><Link /></el-icon></template>
              </el-input>
              <div style="font-size: 12px; color: #909399; margin-top: 4px">
                兼容 OpenAI API 格式，支援 DeepSeek / OpenAI / Groq 等
              </div>
            </el-form-item>

            <el-form-item label="模型名稱">
              <el-input
                v-model="form.model"
                placeholder="deepseek-chat"
                @input="formDirty = true"
              >
                <template #prefix><el-icon><Cpu /></el-icon></template>
              </el-input>
            </el-form-item>

            <el-form-item label="超時 (秒)">
              <el-input-number v-model="form.timeout" :min="10" :max="120" />
            </el-form-item>

            <el-form-item>
              <div style="display: flex; gap: 12px">
                <el-button
                  type="primary"
                  @click="handleSave"
                  :loading="llmStore.saving"
                  :disabled="!formDirty"
                >
                  保存配置
                </el-button>
                <el-button
                  @click="handleTest"
                  :loading="llmStore.testing"
                  :disabled="!form.api_key"
                >
                  測試連接
                </el-button>
                <el-button
                  type="danger"
                  plain
                  @click="handleClear"
                  :disabled="!llmStore.configured"
                >
                  清除配置
                </el-button>
              </div>
            </el-form-item>
          </el-form>

          <el-divider />

          <div style="margin-bottom: 8px; font-weight: 600">快速入門</div>
          <el-table :data="quickStartData" size="small" max-height="200">
            <el-table-column prop="provider" label="提供商" width="120" />
            <el-table-column prop="baseUrl" label="Base URL" min-width="250" />
            <el-table-column prop="model" label="推薦模型" width="160" />
            <el-table-column prop="getKey" label="獲取 API Key" width="160">
              <template #default="{ row }">
                <el-link :href="row.link" type="primary" target="_blank">{{ row.getKey }}</el-link>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="部署信息" name="deploy">
        <el-card>
          <h4>Docker 部署</h4>
          <pre style="background: #f5f7fa; padding: 16px; border-radius: 4px">docker-compose up -d</pre>
          <h4 style="margin-top: 16px">本地開發</h4>
          <pre style="background: #f5f7fa; padding: 16px; border-radius: 4px"># 後端 API
uvicorn api.main:app --reload --port 8000

# 前端開發
cd web && npm run dev</pre>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="定時任務" name="scheduler">
        <el-card>
          <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px">
            <span><el-icon><Timer /></el-icon> 定時爬取任務</span>
            <el-button type="primary" size="small" @click="showSchedulerForm = true" style="margin-left: auto">
              新增任務
            </el-button>
          </div>

          <!-- 新增/編輯表單 -->
          <el-dialog v-model="showSchedulerForm" :title="editingJob ? '編輯任務' : '新增定時任務'" width="500px">
            <el-form :model="schedulerForm" label-width="100px">
              <el-form-item label="任務名稱">
                <el-input v-model="schedulerForm.name" placeholder="例如：每週一爬取" />
              </el-form-item>
              <el-form-item label="關鍵詞">
                <el-select-v2
                  v-model="schedulerForm.keywords"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="輸入關鍵詞"
                  style="width: 100%"
                  :options="[]"
                />
              </el-form-item>
              <el-form-item label="數據源">
                <el-checkbox-group v-model="schedulerForm.sources">
                  <el-checkbox value="jobsdb" label="JobsDB" />
                  <el-checkbox value="jijis" label="JIJIS" />
                  <el-checkbox value="offertoday" label="OfferToday" />
                  <el-checkbox value="indeed" label="Indeed" />
                </el-checkbox-group>
              </el-form-item>
              <el-form-item label="Cron 表達式">
                <el-input v-model="schedulerForm.cron" placeholder="0 6 * * 1 (每週一 6:00)" />
                <div style="font-size: 12px; color: #909399; margin-top: 4px">
                  格式：分 時 日 月 週。每週一 6:00 = 0 6 * * 1
                </div>
              </el-form-item>
              <el-form-item label="啟用">
                <el-switch v-model="schedulerForm.enabled" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="showSchedulerForm = false">取消</el-button>
              <el-button type="primary" @click="saveSchedulerJob" :loading="savingJob">
                {{ editingJob ? '更新' : '新增' }}
              </el-button>
            </template>
          </el-dialog>

          <!-- 任務列表 -->
          <el-table :data="cronJobs" stripe empty-text="暫無定時任務">
            <el-table-column prop="name" label="名稱" min-width="140" />
            <el-table-column label="關鍵詞" min-width="160">
              <template #default="{ row }">
                <el-tag v-for="kw in row.keywords" :key="kw" size="small" style="margin: 1px 2px">{{ kw }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="來源" width="160">
              <template #default="{ row }">
                <el-tag v-for="s in row.sources" :key="s" size="small" type="info" style="margin: 1px 2px">{{ s }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cron" label="Cron" width="110" />
            <el-table-column label="狀態" width="80">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '啟用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="上次執行" width="170">
              <template #default="{ row }">{{ row.last_run ? row.last_run.slice(0, 19) : '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editJob(row)">編輯</el-button>
                <el-button link size="small" @click="runJobNow(row.id)">立即執行</el-button>
                <el-popconfirm title="確認刪除?" @confirm="deleteJob(row.id)">
                  <template #reference>
                    <el-button link type="danger" size="small">刪除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue'
import { useSystemStore } from '@/stores/system'
import { useLLMStore } from '@/stores/llm'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Lock, Link, Cpu } from '@element-plus/icons-vue'

const systemStore = useSystemStore()
const llmStore = useLLMStore()
const activeTab = ref('system')
const formDirty = ref(false)

const form = reactive({
  api_key: '',
  base_url: 'https://api.deepseek.com/v1',
  model: 'deepseek-chat',
  timeout: 30,
})

const quickStartData = [
  { provider: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', model: 'deepseek-chat', getKey: 'DeepSeek', link: 'https://platform.deepseek.com/api_keys' },
  { provider: 'OpenAI', baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini', getKey: 'OpenAI', link: 'https://platform.openai.com/api-keys' },
  { provider: 'Groq', baseUrl: 'https://api.groq.com/openai/v1', model: 'llama-3.3-70b-versatile', getKey: 'Groq', link: 'https://console.groq.com/keys' },
  { provider: '硅基流動', baseUrl: 'https://api.siliconflow.cn/v1', model: 'Qwen/Qwen2.5-7B-Instruct', getKey: '硅基流動', link: 'https://cloud.siliconflow.cn/account/ak' },
  { provider: 'DeepSeek 官方', baseUrl: 'https://api.deepseek.com', model: 'deepseek-chat', getKey: 'DeepSeek', link: 'https://platform.deepseek.com/api_keys' },
]

onMounted(async () => {
  await Promise.all([systemStore.checkHealth(), llmStore.fetchStatus(), fetchCronJobs()])
  if (llmStore.configured) {
    form.base_url = llmStore.baseUrl
    form.model = llmStore.model
  }
  activeTab.value = 'system'
})

async function handleSave() {
  // 如果 api_key 为空且之前已保存，保持原有 key，只更新其他配置
  const payload: Record<string, string | number> = {
    base_url: form.base_url,
    model: form.model,
    timeout: form.timeout,
  }
  // 只有用户修改了 api_key 或之前未配置时才提交
  if (form.api_key || !llmStore.apiKeySet) {
    payload.api_key = form.api_key
  }
  await llmStore.saveConfig(payload)
  formDirty.value = false
  ElMessage.success('LLM 配置已保存')
}

async function handleTest() {
  const result = await llmStore.testConnection()
  if (result.success) {
    ElMessage.success(`連接成功！延遲 ${result.latency_ms}ms`)
  } else {
    ElMessage.error(`連接失敗：${result.message}`)
  }
}

async function handleClear() {
  await ElMessageBox.confirm('確定清除 LLM 配置？API Key 將被移除。', '確認', { type: 'warning' })
  await llmStore.clearConfig()
  form.api_key = ''
  formDirty.value = true
  ElMessage.success('LLM 配置已清除')
}

// ── Scheduler ──
import api from '@/api'
import { Timer } from '@element-plus/icons-vue'

interface CronJobDTO {
  id: string
  name: string
  keywords: string[]
  sources: string[]
  cron: string
  enabled: boolean
  last_run: string | null
  created_at: string
}

const cronJobs = ref<CronJobDTO[]>([])
const showSchedulerForm = ref(false)
const savingJob = ref(false)
const editingJob = ref<CronJobDTO | null>(null)

const schedulerForm = reactive({
  name: '',
  keywords: [] as string[],
  sources: [] as string[],
  cron: '0 6 * * 1',
  enabled: true,
})

async function fetchCronJobs() {
  try {
    const { data } = await api.get('/scheduler/jobs')
    cronJobs.value = data
  } catch { /* ignore */ }
}

function editJob(job: CronJobDTO) {
  editingJob.value = job
  schedulerForm.name = job.name
  schedulerForm.keywords = [...job.keywords]
  schedulerForm.sources = [...job.sources]
  schedulerForm.cron = job.cron
  schedulerForm.enabled = job.enabled
  showSchedulerForm.value = true
}

function resetSchedulerForm() {
  editingJob.value = null
  schedulerForm.name = ''
  schedulerForm.keywords = []
  schedulerForm.sources = []
  schedulerForm.cron = '0 6 * * 1'
  schedulerForm.enabled = true
}

async function saveSchedulerJob() {
  if (!schedulerForm.name || !schedulerForm.keywords.length || !schedulerForm.sources.length) return
  savingJob.value = true
  try {
    if (editingJob.value) {
      await api.put(`/scheduler/jobs/${editingJob.value.id}`, schedulerForm)
    } else {
      await api.post('/scheduler/jobs', schedulerForm)
    }
    showSchedulerForm.value = false
    resetSchedulerForm()
    await fetchCronJobs()
    ElMessage.success(editingJob.value ? '任務已更新' : '任務已創建')
  } catch {
    ElMessage.error('操作失敗')
  } finally {
    savingJob.value = false
  }
}

async function deleteJob(jobId: string) {
  try {
    await api.delete(`/scheduler/jobs/${jobId}`)
    await fetchCronJobs()
    ElMessage.success('任務已刪除')
  } catch {
    ElMessage.error('刪除失敗')
  }
}

async function runJobNow(jobId: string) {
  try {
    const { data } = await api.post(`/scheduler/jobs/${jobId}/run`)
    ElMessage.success(`任務已觸發，任務 ID: ${data.task_id}`)
  } catch {
    ElMessage.error('執行失敗')
  }
}
</script>
