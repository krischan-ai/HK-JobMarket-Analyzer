<template>
  <el-card class="input-panel" shadow="never">
    <template #header>
      <div class="panel-header">
        <span>生成輸入</span>
        <el-button :disabled="store.loading" text @click="store.clear">清空</el-button>
      </div>
    </template>

    <el-form label-position="top">
      <el-form-item label="PDF 簡歷">
        <el-upload
          drag
          :auto-upload="false"
          :show-file-list="false"
          accept="application/pdf,.pdf"
          :on-change="handleFile"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">拖放 PDF 或點擊上傳</div>
          <template #tip>
            <div class="upload-tip">
              {{ store.resumeFileName || '文件僅用於本次解析，不會自動保存原文。' }}
            </div>
          </template>
        </el-upload>
      </el-form-item>

      <el-form-item label="簡歷 / 個人資料文本">
        <el-input
          v-model="store.resumeText"
          type="textarea"
          :rows="12"
          resize="vertical"
          placeholder="貼上基礎簡歷、項目經歷或個人資料..."
        />
      </el-form-item>

      <div class="form-grid">
        <el-form-item label="目標崗位">
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

      <div class="form-grid">
        <el-form-item label="目標市場">
          <el-input v-model="store.targetMarket" />
        </el-form-item>
        <el-form-item label="召回岗位數">
          <el-input-number v-model="store.topKJobs" :min="1" :max="20" controls-position="right" />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item label="語言">
          <el-select v-model="store.language">
            <el-option label="English" value="en" />
            <el-option label="繁體中文" value="zh-Hant" />
            <el-option label="簡體中文" value="zh-Hans" />
          </el-select>
        </el-form-item>
        <el-form-item label="風格">
          <el-select v-model="store.style">
            <el-option label="Professional" value="professional" />
            <el-option label="Technical" value="technical" />
            <el-option label="Management" value="management" />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item label="敘事角度">
        <div class="angle-picker">
          <el-input v-model="store.narrativeAngle" placeholder="例如：AI 医疗影像 / 后端工程 / 数据分析转 AI" clearable />
          <div class="angle-tags">
            <el-check-tag
              v-for="angle in angleOptions"
              :key="angle.value"
              :checked="store.narrativeAngle === angle.value"
              @change="() => (store.narrativeAngle = angle.value)"
            >
              {{ angle.label }}
            </el-check-tag>
          </div>
        </div>
      </el-form-item>

      <el-alert v-if="store.error" :title="store.error" type="error" show-icon :closable="false" />

      <el-button
        class="submit-button"
        type="primary"
        :loading="store.loading || store.uploading"
        :disabled="!store.canSubmit"
        @click="store.generate"
      >
        生成目標簡歷
      </el-button>
    </el-form>
  </el-card>
</template>

<script lang="ts" setup>
import { UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import { useResumeGenerateStore } from '@/stores/resumeGenerate'

const store = useResumeGenerateStore()
const angleOptions = [
  { label: '工程交付', value: 'engineering' },
  { label: 'AI 應用', value: 'ai' },
  { label: '數據分析', value: 'data' },
  { label: '產品協作', value: 'product' },
  { label: '運營效率', value: 'operations' },
  { label: '技術管理', value: 'management' },
]

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

async function handleFile(uploadFile: UploadFile) {
  const file = uploadFile.raw
  if (!file) return
  await store.extractPdf(file)
}
</script>

<style scoped>
.input-panel {
  min-width: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.upload-icon {
  color: #409eff;
  font-size: 32px;
}

.upload-text {
  color: #303133;
  font-size: 14px;
}

.upload-tip {
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}

.form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

.form-grid:first-of-type {
  grid-template-columns: 1fr;
}

.role-picker {
  display: grid;
  grid-template-columns: minmax(180px, 0.9fr) minmax(180px, 1fr);
  gap: 8px;
  width: 100%;
}

.angle-picker {
  display: grid;
  gap: 8px;
}

.angle-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.submit-button {
  width: 100%;
  margin-top: 10px;
}

@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .role-picker {
    grid-template-columns: 1fr;
  }
}
</style>
