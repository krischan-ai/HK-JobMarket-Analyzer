<template>
  <el-card shadow="never" class="input-card">
    <template #header>
      <div class="card-header">
        <span>輸入內容</span>
        <el-tag type="info" effect="plain">不保存原文</el-tag>
      </div>
    </template>

    <el-form label-position="top">
      <el-form-item label="簡歷原文">
        <div class="resume-field">
          <el-upload
            class="pdf-upload"
            drag
            accept="application/pdf,.pdf"
            :show-file-list="false"
            :auto-upload="false"
            :disabled="store.uploading"
            :on-change="onPdfChange"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">
              <span v-if="store.uploading">解析中…</span>
              <span v-else-if="store.resumeFileName">已導入：{{ store.resumeFileName }}（可在下方編輯）</span>
              <span v-else>拖入或點擊上傳 PDF 簡歷，自動填入下方文本框</span>
            </div>
          </el-upload>

          <el-input
            v-model="store.resumeText"
            type="textarea"
            :rows="13"
            maxlength="50000"
            show-word-limit
            placeholder="貼上你的簡歷內容，或上傳 PDF 自動填入後再編輯"
          />
        </div>
      </el-form-item>

      <el-form-item label="目標 JD（選填）">
        <div class="resume-field">
          <el-input
            v-model="store.jdText"
            type="textarea"
            :rows="11"
            maxlength="20000"
            show-word-limit
            placeholder="貼上目標崗位 JD（選填）。留空則自動用知識庫相似崗位分析"
          />
          <el-alert
            v-if="store.knowledgeBaseMode"
            type="info"
            :closable="false"
            show-icon
            class="kb-hint"
            title="未填寫目標 JD，將基於香港知識庫相似崗位生成市場畫像進行分析（可在下方填寫目標職位以聚焦方向）"
          />
        </div>
      </el-form-item>

      <div class="optional-grid">
        <el-form-item label="目標職位">
          <el-input v-model="store.targetRole" placeholder="Backend Engineer" clearable />
        </el-form-item>
        <el-form-item label="JD 連結">
          <el-input v-model="store.jdUrl" placeholder="https://..." clearable />
        </el-form-item>
      </div>

      <el-form-item label="重試次數">
        <el-input-number v-model="store.maxRetries" :min="0" :max="5" />
      </el-form-item>

      <div class="actions">
        <el-button type="primary" :loading="store.loading" :disabled="!store.canSubmit" @click="store.polishStream">
          開始潤色
        </el-button>
        <el-button :disabled="store.loading" @click="store.clear">清空</el-button>
      </div>

      <el-alert
        v-if="store.error"
        :title="store.error"
        type="error"
        show-icon
        :closable="false"
        class="error-alert"
      />
    </el-form>
  </el-card>
</template>

<script lang="ts" setup>
import { UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import { useResumeStore } from '@/stores/resume'

const store = useResumeStore()

function onPdfChange(file: UploadFile) {
  if (file.raw) {
    store.extractPdf(file.raw)
  }
}
</script>

<style scoped>
.input-card {
  height: 100%;
}

.card-header,
.actions,
.optional-grid {
  display: flex;
  gap: 12px;
}

.card-header {
  align-items: center;
  justify-content: space-between;
}

.optional-grid {
  align-items: flex-start;
}

.optional-grid :deep(.el-form-item) {
  flex: 1;
}

.actions {
  align-items: center;
  margin-top: 8px;
}

.error-alert {
  margin-top: 16px;
}

.resume-field {
  width: 100%;
}

.pdf-upload {
  margin-bottom: 12px;
}

.kb-hint {
  margin-top: 8px;
}

.pdf-upload :deep(.el-upload-dragger) {
  padding: 14px;
}

.upload-icon {
  font-size: 24px;
  color: var(--el-color-primary);
}

.upload-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

@media (max-width: 900px) {
  .optional-grid {
    display: block;
  }
}
</style>
