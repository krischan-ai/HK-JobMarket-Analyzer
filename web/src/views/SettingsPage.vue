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
                placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
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
  await Promise.all([systemStore.checkHealth(), llmStore.fetchStatus()])
  if (llmStore.configured) {
    form.base_url = llmStore.baseUrl
    form.model = llmStore.model
  }
  activeTab.value = 'system'
})

async function handleSave() {
  await llmStore.saveConfig({ ...form })
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
</script>
