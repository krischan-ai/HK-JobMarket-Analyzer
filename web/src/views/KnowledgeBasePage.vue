<template>
  <div>
    <h2 style="margin-top: 0">知識庫總覽</h2>

    <!-- 語義搜索 -->
    <el-card style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; align-items: center; gap: 12px">
          <span><el-icon><Search /></el-icon> 語義搜索</span>
          <el-tag :type="vectorReady ? 'success' : 'info'" size="small">
            {{ vectorReady ? `向量索引就緒 (${vectorDocCount} 文檔)` : '向量索引未初始化' }}
          </el-tag>
          <span style="margin-left: auto; display: flex; gap: 8px">
            <el-button size="small" @click="rebuildIndex" :loading="rebuilding" :disabled="!vectorReady">
              重建索引
            </el-button>
            <el-button size="small" type="danger" @click="clearIndex" :disabled="!vectorReady">
              清空
            </el-button>
          </span>
        </div>
      </template>
      <el-input
        v-model="searchQuery"
        placeholder="輸入自然語言查詢，例如：需要 Python 和 AWS 的後端開發崗位"
        @keyup.enter="doSemanticSearch"
        clearable
      >
        <template #append>
          <el-button :loading="searching" @click="doSemanticSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
        </template>
      </el-input>

      <div v-if="searchResults.length" style="margin-top: 12px">
        <div v-for="r in searchResults" :key="r.doc_id" style="padding: 10px 0; border-bottom: 1px solid #ebeef5">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px">
            <strong>{{ r.title }}</strong>
            <el-tag size="small" type="info">{{ r.company }}</el-tag>
            <el-tag size="small">{{ r.location }}</el-tag>
            <span style="font-size: 12px; color: #67c23a">相似度 {{ (r.score * 100).toFixed(0) }}%</span>
          </div>
          <div style="font-size: 13px; color: #606266; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
            {{ r.snippet }}
          </div>
        </div>
      </div>
      <el-empty v-else-if="searchPerformed" description="未找到匹配結果" :image-size="60" />
    </el-card>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="8">
        <el-card>
          <template #header><strong>數據來源佔比</strong></template>
          <SourcePieChart :data="sourceData" :height="300" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><strong>技能熱度排行</strong></template>
          <SkillBarChart :data="skillData" :height="300" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><strong>版本歷史</strong></template>
          <DataTable :data="versions" max-height="250" :stripe="false">
            <el-table-column prop="version" label="版本" width="70" />
            <el-table-column prop="records" label="記錄數" width="70" />
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="date" label="日期" width="100" />
          </DataTable>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { knowledgeApi } from '@/api/knowledge'
import type { SemanticSearchResult } from '@/api/knowledge'
import SourcePieChart from '@/components/charts/SourcePieChart.vue'
import SkillBarChart from '@/components/charts/SkillBarChart.vue'
import DataTable from '@/components/common/DataTable.vue'

const sourceData = ref<{ source: string; count: number }[]>([])
const skillData = ref<{ skill: string; count: number }[]>([])
const versions = ref<{ version: string; records: string; description: string; date: string }[]>([])

// Semantic search state
const searchQuery = ref('')
const searchResults = ref<SemanticSearchResult[]>([])
const searching = ref(false)
const searchPerformed = ref(false)
const vectorReady = ref(false)
const vectorDocCount = ref(0)
const rebuilding = ref(false)

async function doSemanticSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  searchPerformed.value = true
  try {
    const { data } = await knowledgeApi.semanticSearch(searchQuery.value)
    if (data.available) {
      searchResults.value = data.results
    } else {
      ElMessage.warning(data.message || '向量搜索不可用')
      searchResults.value = []
    }
  } catch {
    ElMessage.error('搜索失敗')
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

async function checkVectorStatus() {
  try {
    const { data } = await knowledgeApi.vectorStatus()
    vectorReady.value = data.available
    vectorDocCount.value = data.doc_count
  } catch {
    vectorReady.value = false
  }
}

async function rebuildIndex() {
  rebuilding.value = true
  try {
    const { data } = await knowledgeApi.vectorRebuild()
    if (data.success) {
      ElMessage.success(`索引重建完成，共 ${data.doc_count} 篇文檔`)
      vectorDocCount.value = data.doc_count || 0
    } else {
      ElMessage.error(data.message || '重建失敗')
    }
  } catch {
    ElMessage.error('重建失敗')
  } finally {
    rebuilding.value = false
  }
}

async function clearIndex() {
  try {
    await knowledgeApi.vectorClear()
    ElMessage.success('索引已清空')
    vectorDocCount.value = 0
  } catch {
    ElMessage.error('清空失敗')
  }
}

onMounted(async () => {
  const [sr, sk, vr] = await Promise.all([
    api.get('/stats/source-distribution'),
    api.get('/knowledge/skill-frequency', { params: { top_n: 15 } }),
    api.get('/knowledge/versions'),
  ])
  sourceData.value = sr.data
  skillData.value = sk.data
  versions.value = vr.data
  checkVectorStatus()
})
</script>
