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
        <el-input
          v-model="store.resumeText"
          type="textarea"
          :rows="13"
          maxlength="50000"
          show-word-limit
          placeholder="貼上你的簡歷內容，建議包含工作經驗、項目、技能和教育背景"
        />
      </el-form-item>

      <el-form-item label="目標 JD">
        <el-input
          v-model="store.jdText"
          type="textarea"
          :rows="11"
          maxlength="20000"
          show-word-limit
          placeholder="貼上目標崗位 JD，英文或中英文混合均可"
        />
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
        <el-button type="primary" :loading="store.loading" :disabled="!store.canSubmit" @click="store.polish">
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
import { useResumeStore } from '@/stores/resume'

const store = useResumeStore()
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

@media (max-width: 900px) {
  .optional-grid {
    display: block;
  }
}
</style>
