<template>
  <div>
    <h2 style="margin-top: 0">上傳數據</h2>
    <FileUploader
      accept=".csv,.json,.xlsx"
      accept-label="CSV / JSON / Excel"
      tip="支援格式: CSV (UTF-8), JSON, Excel (.xlsx)，最大 50MB / 10,000 行"
      @file-change="handleFile"
    />

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

    <ProcessResultSummary v-if="uploadStore.result" :result="uploadStore.result" style="margin-top: 16px" />
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { useUploadStore } from '@/stores/upload'
import FileUploader from '@/components/upload/FileUploader.vue'
import ProcessResultSummary from '@/components/upload/ProcessResultSummary.vue'

const uploadStore = useUploadStore()
const file = ref<File | null>(null)
const sourceTag = ref('user_upload')
const runCleaning = ref(true)
const runExtraction = ref(true)

function handleFile(f: File) {
  file.value = f
}

async function doUpload() {
  if (!file.value) return
  await uploadStore.uploadFile(file.value, sourceTag.value)
}
</script>
