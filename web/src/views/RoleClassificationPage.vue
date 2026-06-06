<template>
  <div>
    <h2 style="margin-top: 0"><el-icon><Aim /></el-icon> 崗位角色分類</h2>

    <!-- 狀態概覽 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 28px; font-weight: bold; color: #409eff">{{ store.total }}</div>
            <div style="color: #909399">總崗位數</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 28px; font-weight: bold; color: #67c23a">{{ store.classified }}</div>
            <div style="color: #909399">已分類</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 28px; font-weight: bold; color: #e6a23c">{{ store.coverageRate }}%</div>
            <div style="color: #909399">覆蓋率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <el-tag :type="store.llmAvailable ? 'success' : 'info'" size="large">
              {{ store.llmAvailable ? 'LLM 驅動' : '規則引擎' }}
            </el-tag>
            <div style="color: #909399; margin-top: 6px">分類模式</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 分類控制區 -->
    <el-card style="margin-bottom: 16px">
      <template #header>
        <span><el-icon><DataAnalysis /></el-icon> 執行分類</span>
      </template>
      <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap">
        <span>批次大小:</span>
        <el-input-number v-model="batchSize" :min="1" :max="50" :disabled="store.running" size="small" />
        <el-button
          type="primary"
          :loading="store.running"
          :disabled="store.running"
          @click="handleRun"
          size="large"
        >
          <el-icon><VideoPlay /></el-icon>
          {{ store.running ? '分類中...' : '開始分類全部崗位' }}
        </el-button>
        <el-tag v-if="store.llmMode" type="success" size="small">使用 LLM 智能分類</el-tag>
        <el-tag v-else-if="store.duration" type="warning" size="small">使用關鍵詞規則分類</el-tag>
        <span v-if="store.duration" style="font-size: 13px; color: #909399">
          耗時 {{ (store.duration / 1000).toFixed(1) }}s
        </span>
      </div>

      <!-- 進度條 -->
      <div v-if="store.running || store.progress > 0" style="margin-top: 16px">
        <el-progress
          :percentage="store.progress"
          :stroke-width="22"
          :text-inside="true"
          :status="store.running ? '' : 'success'"
        />
        <div style="margin-top: 8px; font-size: 13px; color: #606266">
          {{ store.message }}
        </div>
      </div>
    </el-card>

    <!-- 保险岗位检测 -->
    <el-card v-if="store.results.length && insuranceStats.hasAny" style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; align-items: center; gap: 12px">
          <span style="color: #e6a23c; font-weight: bold">⚠ 疑似保險銷售</span>
          <el-tag type="warning" size="small">
            {{ insuranceStats.count }} / {{ store.total }} ({{ insuranceStats.pct }}%)
          </el-tag>
          <span v-if="store.llmInsuranceCount > 0" style="font-size: 13px; color: #f56c6c">
            LLM 確認 {{ store.llmInsuranceCount }} 個
          </span>
          <el-button
            type="warning"
            size="small"
            style="margin-left: auto"
            :loading="store.reviewing"
            :disabled="!store.llmAvailable || store.reviewing"
            @click="handleReviewInsurance"
          >
            🤖 LLM 復審
          </el-button>
        </div>
      </template>
    </el-card>

    <!-- 角色分佈 + 技能概覽 -->
    <el-row v-if="store.roleStats.length" :gutter="16" style="margin-bottom: 16px">
      <el-col :span="12">
        <el-card>
          <template #header><strong>角色分佈</strong></template>
          <div v-for="r in store.roleStats" :key="r.role_id" style="display: flex; align-items: center; margin-bottom: 8px">
            <el-tag
              :type="tagType(r.role_id)"
              size="small"
              style="width: 110px; text-align: center; cursor: pointer"
              @click="store.roleFilter = store.roleFilter === r.role_id ? '' : r.role_id"
            >
              {{ r.role_name }}
            </el-tag>
            <el-progress
              :percentage="Math.round(r.count / store.total * 100)"
              :stroke-width="16"
              :text-inside="false"
              style="flex: 1; margin: 0 8px"
            />
            <span style="font-size: 12px; width: 30px; text-align: right">{{ r.count }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="display: flex; align-items: center; gap: 8px">
              <strong>技術棧詞雲</strong>
              <span style="font-size: 12px; color: #909399">（共 {{ store.uniqueSkills.length }} 項）</span>
            </div>
          </template>
          <div style="max-height: 320px; overflow-y: auto; display: flex; flex-wrap: wrap; gap: 4px">
            <el-tag
              v-for="sk in store.uniqueSkills"
              :key="sk"
              size="small"
              style="cursor: default"
            >{{ sk }}</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 分類結果表格 -->
    <el-card v-if="store.results.length">
      <template #header>
        <div style="display: flex; align-items: center; gap: 12px">
          <strong>分類結果</strong>
          <span style="font-size: 13px; color: #909399">共 {{ store.filteredResults.length }} 條</span>
          <el-select
            v-model="store.roleFilter"
            placeholder="按角色篩選"
            clearable
            size="small"
            style="width: 160px; margin-left: auto"
          >
            <el-option v-for="r in store.roleStats" :key="r.role_id" :label="r.role_name" :value="r.role_id" />
          </el-select>
        </div>
      </template>

      <el-table
        :data="store.filteredResults"
        stripe
        max-height="600"
        :default-sort="{ prop: 'role_confidence', order: 'ascending' }"
        :row-class-name="rowClassName"
      >
        <el-table-column prop="title" label="崗位名稱" min-width="200" show-overflow-tooltip />
        <el-table-column prop="company" label="公司" width="140" show-overflow-tooltip />
        <el-table-column label="角色" width="150">
          <template #default="{ row }">
            <div style="display: flex; flex-direction: column; gap: 2px">
              <el-tag :type="tagType(row.role_id)" size="small">{{ row.role_name }}</el-tag>
              <el-tag
                v-if="row.is_insurance_sales && !row.llm_explanation"
                type="warning"
                size="small"
                effect="dark"
              >
                ⚠ 疑保險 {{ row.insurance_score }}分
              </el-tag>
              <el-tag
                v-if="row.llm_is_insurance && row.llm_explanation"
                type="danger"
                size="small"
                effect="dark"
              >
                ⚠ 保險崗位
              </el-tag>
              <span
                v-if="row.llm_is_insurance && row.llm_explanation"
                style="font-size: 11px; color: #f56c6c; line-height: 1.3; max-width: 140px"
              >{{ row.llm_explanation }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="90">
          <template #default="{ row }">
            <el-tag
              :type="row.role_confidence === 'high' ? 'success' : row.role_confidence === 'medium' ? 'warning' : 'info'"
              size="small"
            >
              {{ row.role_confidence === 'high' ? '高' : row.role_confidence === 'medium' ? '中' : '低' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="薪資 (HKD/月)" width="160">
          <template #default="{ row }">
            <span v-if="row.salary_min > 0">{{ Math.round(row.salary_min).toLocaleString() }}
              <span v-if="row.salary_max > row.salary_min"> - {{ Math.round(row.salary_max).toLocaleString() }}</span>
            </span>
            <span v-else style="color: #c0c4cc">面議</span>
          </template>
        </el-table-column>
        <el-table-column label="技術棧" min-width="280">
          <template #default="{ row }">
            <span v-if="row.skills && row.skills.length">
              <el-tooltip
                v-for="(sk, i) in row.skills"
                :key="i"
                :content="skillCategoryName(sk.category)"
                placement="top"
              >
                <el-tag
                  size="small"
                  :type="skillTagType(sk.category)"
                  effect="plain"
                  style="margin: 1px 2px"
                >
                  {{ sk.name }}
                </el-tag>
              </el-tooltip>
            </span>
            <span v-else style="color: #c0c4cc">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="地點" width="100" show-overflow-tooltip />
        <el-table-column prop="source" label="來源" width="90" />
      </el-table>
    </el-card>

    <!-- 空狀態 -->
    <el-empty v-if="!store.running && !store.results.length" description="尚未執行分類，請點擊上方按鈕開始" />
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useClassificationStore } from '@/stores/classification'

const store = useClassificationStore()
const batchSize = ref(5)

const roleColors: Record<string, string> = {
  frontend: '', backend: 'success', fullstack: 'warning',
  mobile: 'danger', data_scientist: '', ml_engineer: 'success',
  data_engineer: 'success', data_science: 'success',
  devops: 'info', qa: 'warning', security: 'danger',
  solution_architect: 'warning', engineering_manager: 'danger',
  it_analyst: 'info',
  product: 'success', design: '', blockchain: 'warning',
  ai_prompt_engineer: 'danger', ai_model_training: 'warning',
  ai_agent_dev: '', ai_application: 'success',
  other: 'info',
}

// 技能类别颜色映射（按 API 返回的英文字段名）
const skillCategoryColors: Record<string, string> = {
  programming_languages: '',
  frameworks_libraries: 'success',
  cloud_devops: 'warning',
  databases: 'danger',
  soft_skills: 'info',
}

// 技能类别中文名
const skillCategoryNames: Record<string, string> = {
  programming_languages: '程式語言',
  frameworks_libraries: '框架/庫',
  cloud_devops: '雲/運維',
  databases: '數據庫',
  soft_skills: '軟技能',
}

function tagType(roleId: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return (roleColors[roleId] || 'info') as '' | 'success' | 'warning' | 'danger' | 'info'
}

function skillTagType(cat: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return (skillCategoryColors[cat] || 'info') as '' | 'success' | 'warning' | 'danger' | 'info'
}

function skillCategoryName(cat: string): string {
  return skillCategoryNames[cat] || cat
}

function rowClassName({ row }: { row: { is_insurance_sales: boolean } }) {
  return row.is_insurance_sales ? 'insurance-suspect-row' : ''
}

const insuranceStats = computed(() => {
  const count = store.insuranceCount
  return {
    count,
    pct: store.total > 0 ? Math.round(count / store.total * 100 * 10) / 10 : 0,
    hasAny: count > 0,
  }
})

async function handleReviewInsurance() {
  try {
    await store.reviewInsurance()
    ElMessage.success(store.message)
  } catch {
    ElMessage.error('LLM 復審失敗')
  }
}

async function handleRun() {
  try {
    await store.runWithPoll(batchSize.value)
    ElMessage.success(store.message)
  } catch {
    ElMessage.error('分類失敗')
  }
}

onMounted(() => {
  store.fetchStatus()
  store.fetchDistribution()
})
</script>

<style scoped>
:deep(.insurance-suspect-row) {
  background-color: #fef0e8 !important;
}
:deep(.insurance-suspect-row:hover > td) {
  background-color: #fde2d0 !important;
}
</style>
