<template>
  <div>
    <h2 style="margin-top: 0">⚙️ 系統設置</h2>

    <el-tabs>
      <el-tab-pane label="系統信息">
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

      <el-tab-pane label="LLM 配置">
        <el-card>
          <el-alert title="提示" type="info" style="margin-bottom: 16px" :closable="false">
            請在 Streamlit 面板中配置 LLM（⚙️ 模型配置頁面），或編輯 config/llm_config.json 文件。
          </el-alert>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="API Key">********</el-descriptions-item>
            <el-descriptions-item label="Base URL">https://api.deepseek.com/v1</el-descriptions-item>
            <el-descriptions-item label="模型">deepseek-chat</el-descriptions-item>
            <el-descriptions-item label="狀態"><el-tag type="warning">未配置</el-tag></el-descriptions-item>
          </el-descriptions>
          <div style="margin-top: 16px">
            <el-button @click="$router.push('/upload')">前往 Streamlit 面板進行配置</el-button>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="部署信息">
        <el-card>
          <h4>Docker 部署</h4>
          <pre style="background: #f5f7fa; padding: 16px; border-radius: 4px">docker-compose up -d</pre>
          <h4 style="margin-top: 16px">本地開發</h4>
          <pre style="background: #f5f7fa; padding: 16px; border-radius: 4px"># 後端
uvicorn api.main:app --reload --port 8000

# 前端
cd web && npm run dev

# 數據看板
streamlit run src/app.py</pre>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script lang="ts" setup>
import { onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()
onMounted(() => systemStore.checkHealth())
</script>
