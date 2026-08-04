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
          <div class="role-picker">
            <el-select
              v-model="store.targetRoleId"
              placeholder="選擇標準計算機崗位分類"
              filterable
              clearable
              @change="onRoleChange"
              @clear="onRoleClear"
            >
              <el-option-group
                v-for="group in roleGroups"
                :key="group.label"
                :label="group.label"
              >
                <el-option
                  v-for="role in group.options"
                  :key="role.id"
                  :label="role.name"
                  :value="role.id"
                />
              </el-option-group>
            </el-select>
            <el-input v-model="store.targetRole" placeholder="或輸入自定義目標職位" clearable />
          </div>
        </el-form-item>
      </div>

      <div class="optional-grid">
        <el-form-item label="目標市場">
          <el-select v-model="store.targetMarket" placeholder="自動判斷（默認香港）" clearable>
            <el-option label="香港" value="香港" />
            <el-option label="中國大陸" value="中國大陸" />
            <el-option label="美國" value="美國" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="投遞狀態">
          <el-select v-model="store.applicationStatus" placeholder="未確認" clearable>
            <el-option label="未投遞" value="not_applied" />
            <el-option label="已投遞" value="applied" />
            <el-option label="未確認" value="unknown" />
          </el-select>
        </el-form-item>
      </div>

      <div class="optional-grid retry-grid">
        <el-form-item label="JD 連結">
          <el-input v-model="store.jdUrl" placeholder="https://..." clearable />
        </el-form-item>
        <el-form-item label="重試次數">
          <el-input-number v-model="store.maxRetries" :min="0" :max="5" />
        </el-form-item>
      </div>

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

const roleGroups = [
  {
    label: '開發工程',
    options: [
      { id: 'frontend', name: '前端開發' },
      { id: 'backend', name: '後端開發' },
      { id: 'fullstack', name: '全棧開發' },
      { id: 'mobile', name: '移動開發' },
    ],
  },
  {
    label: '數據與 AI',
    options: [
      { id: 'data_scientist', name: '數據科學家' },
      { id: 'data_science', name: '數據科學（通用）' },
      { id: 'data_engineer', name: '數據工程' },
      { id: 'ml_engineer', name: '機器學習工程師' },
      { id: 'ai_application', name: 'AI 應用開發' },
      { id: 'ai_agent_dev', name: 'AI Agent 開發' },
      { id: 'ai_model_training', name: '模型訓練/微調' },
      { id: 'ai_prompt_engineer', name: '提示詞工程師' },
    ],
  },
  {
    label: '基礎設施與品質',
    options: [
      { id: 'devops', name: 'DevOps / SRE' },
      { id: 'qa', name: '質量保證' },
      { id: 'security', name: '安全工程' },
    ],
  },
  {
    label: '架構、分析與管理',
    options: [
      { id: 'solution_architect', name: '解決方案架構師' },
      { id: 'engineering_manager', name: '工程經理/技術主管' },
      { id: 'it_analyst', name: 'IT 分析師/系統分析師' },
    ],
  },
  {
    label: '產品、設計與新興方向',
    options: [
      { id: 'product', name: '產品管理' },
      { id: 'design', name: '設計師' },
      { id: 'blockchain', name: '區塊鏈' },
      { id: 'other', name: '其他' },
    ],
  },
]

const roleNameById = new Map(roleGroups.flatMap((group) => group.options.map((role) => [role.id, role.name])))

function onRoleChange(value: string) {
  store.targetRole = roleNameById.get(value) || store.targetRole
}

function onRoleClear() {
  store.targetRole = ''
}

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

.retry-grid :deep(.el-form-item:first-child) {
  flex: 1 1 auto;
}

.retry-grid :deep(.el-form-item:last-child) {
  flex: 0 0 140px;
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

.role-picker {
  display: grid;
  grid-template-columns: minmax(180px, 0.9fr) minmax(180px, 1fr);
  gap: 8px;
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

  .role-picker {
    grid-template-columns: 1fr;
  }
}
</style>
