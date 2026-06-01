<template>
  <div>
    <h2 style="margin-top: 0">📤 上傳數據</h2>
    <el-card>
      <el-upload
        drag
        :auto-upload="false"
        :on-change="handleFile"
        :limit="1"
        accept=".csv,.json,.xlsx"
      >
        <el-icon :size="48"><UploadFilled /></el-icon>
        <div style="margin-top: 12px">拖拽或點擊上傳 CSV / JSON / Excel 文件</div>
        <template #tip><div style="margin-top: 8px">支援格式: CSV (UTF-8), JSON, Excel (.xlsx)，最大 50MB / 10,000 行</div></template>
      </el-upload>
    </el-card>

    <el-card v-if="file" style="margin-top: 16px">
      <template #header><strong>文件信息</strong></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="文件名">{{ file.name }}</el-descriptions-item>
        <el-descriptions-item label="大小">{{ (file.size / 1024).toFixed(1) }} KB</el-descriptions-item>
        <el-descriptions-item label="來源標籤">
          <el-input v-model="sourceTag" placeholder="user_upload" style="width: 200px" />
        </el-descriptions-item>
        <el-descriptions-item label="處理選項">
          <el-checkbox v-model="runCleaning">執行清洗</el-checkbox>
          <el-checkbox v-model="runExtraction" style="margin-left: 12px">技能提取</el-checkbox>
        </el-descriptions-item>
      </el-descriptions>

      <div style="margin-top: 16px">
        <el-button type="primary" @click="doUpload" :loading="uploadStore.uploading">開始上傳處理</el-button>
      </div>
    </el-card>

    <el-card v-if="uploadStore.result" style="margin-top: 16px">
      <template #header><strong>處理結果</strong></template>
      <el-row :gutter="16">
        <el-col :span="4"><el-statistic title="總記錄" :value="uploadStore.result.total" /></el-col>
        <el-col :span="4"><el-statistic title="成功" :value="uploadStore.result.success" /></el-col>
        <el-col :span="4"><el-statistic title="跳過" :value="uploadStore.result.skipped" /></el-col>
        <el-col :span="4"><el-statistic title="新增" :value="uploadStore.result.new_records" /></el-col>
        <el-col :span="4"><el-statistic title="耗時(ms)" :value="uploadStore.result.duration_ms" /></el-col>
        <el-col :span="4"><el-statistic title="錯誤" :value="uploadStore.result.errors.length" /></el-col>
      </el-row>
      <el-alert v-for="e in uploadStore.result.errors" :key="e" :title="e" type="error" style="margin-top: 8px" v-if="uploadStore.result.errors.length" />
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { useUploadStore } from '@/stores/upload'
import type { UploadFile } from 'element-plus'

const uploadStore = useUploadStore()
const file = ref<File | null>(null)
const sourceTag = ref('user_upload')
const runCleaning = ref(true)
const runExtraction = ref(true)

function handleFile(f: UploadFile) {
  file.value = f.raw || null
}

async function doUpload() {
  if (!file.value) return
  await uploadStore.uploadFile(file.value, sourceTag.value)
}
</script>
