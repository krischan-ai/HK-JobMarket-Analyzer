<template>
  <div class="salary-page">
    <div class="page-header">
      <h2>薪資分析</h2>
      <div class="header-actions">
        <el-tag :type="analysisStatus.type">{{ analysisStatus.text }}</el-tag>
        <el-button :loading="statsStore.salaryAnalysisLoading" type="primary" @click="refreshAnalysis">
          重新生成分析
        </el-button>
      </div>
    </div>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <StatCard label="平均月薪 (HKD)" :value="stats.avg" color="#409EFF" />
      </el-col>
      <el-col :span="6">
        <StatCard label="最低月薪 (HKD)" :value="stats.min" color="#67C23A" />
      </el-col>
      <el-col :span="6">
        <StatCard label="最高月薪 (HKD)" :value="stats.max" color="#E6A23C" />
      </el-col>
      <el-col :span="6">
        <StatCard label="中位月薪 (HKD)" :value="stats.median" color="#909399" />
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <el-card>
          <template #header><strong>薪资趋势</strong></template>
          <TrendLineChart
            :height="460"
            :data="salaryData.map(d => ({ label: d.location, value: d.avg }))"
          />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="12">
        <el-card>
          <template #header><strong>各區域薪資區間</strong></template>
          <SalaryBoxChart :data="salaryData" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><strong>Top 15 高薪地區</strong></template>
          <v-chart :option="topLocationOption" autoresize style="height: 400px" v-if="topLocationOption" />
          <el-skeleton :rows="6" animated v-else />
        </el-card>
      </el-col>
    </el-row>

    <section class="analysis-section">
      <div class="section-header">
        <h3>薪资智能总结</h3>
        <el-tag :type="analysisStatus.type">{{ analysisStatus.text }}</el-tag>
      </div>

      <el-alert
        v-if="statsStore.salaryAnalysisError"
        :title="statsStore.salaryAnalysisError"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 16px"
      />
      <el-alert
        v-else-if="statsStore.salaryAnalysis?.warning"
        :title="statsStore.salaryAnalysis.warning"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 16px"
      />

      <div v-if="statsStore.salaryAnalysisLoading" class="loading-state">
        <el-alert title="AI 正在调用薪资知识库并生成分析。原始数据不变时后续会直接使用缓存。" type="info" show-icon :closable="false" />
        <el-skeleton :rows="8" animated />
      </div>
      <el-row v-else :gutter="16">
        <el-col
          v-for="section in statsStore.salaryAnalysis?.sections || []"
          :key="section.key || section.title"
          :span="24"
          class="analysis-col"
        >
          <el-card class="analysis-card">
            <template #header><strong>{{ section.title }}</strong></template>
            <v-chart class="analysis-chart" :option="analysisChartOption(section)" autoresize />
            <p class="summary">{{ section.summary }}</p>
            <div v-if="section.evidence?.length" class="evidence-list">
              <span v-for="(item, idx) in section.evidence.slice(0, 8)" :key="idx">
                {{ formatEvidence(item) }}
              </span>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </section>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from 'vue'
import VChart from 'vue-echarts'
import api from '@/api'
import { useStatsStore } from '@/stores/stats'
import StatCard from '@/components/common/StatCard.vue'
import SalaryBoxChart from '@/components/charts/SalaryBoxChart.vue'
import TrendLineChart from '@/components/charts/TrendLineChart.vue'
import type { SalaryDistribution, TechTrendSection } from '@/types'

const statsStore = useStatsStore()
const stats = reactive({ avg: '-', min: '-', max: '-', median: '-' })
const salaryData = ref<SalaryDistribution[]>([])

const analysisStatus = computed(() => {
  if (statsStore.salaryAnalysisLoading) return { text: 'AI 分析中', type: 'warning' as const }
  if (!statsStore.salaryAnalysis) return { text: '待生成', type: 'info' as const }
  if (statsStore.salaryAnalysis.from_cache || statsStore.salaryAnalysis.analysis_status === 'cached') {
    return { text: '使用缓存', type: 'success' as const }
  }
  if (statsStore.salaryAnalysis.llm_used) return { text: 'LLM 已完成', type: 'success' as const }
  return { text: '本地兜底摘要', type: 'warning' as const }
})

onMounted(async () => {
  await Promise.all([
    loadSalaryData(),
    loadAnalysis(false),
  ])
})

async function loadSalaryData() {
  const { data } = await api.get('/stats/salary-by-location')
  salaryData.value = data
  if (data.length) {
    const avgs = data.map((d: SalaryDistribution) => d.avg).filter((v: number) => v > 0).sort((a: number, b: number) => a - b)
    stats.min = Math.round(avgs[0]).toLocaleString()
    stats.max = Math.round(avgs[avgs.length - 1]).toLocaleString()
    const sum = avgs.reduce((a: number, b: number) => a + b, 0)
    stats.avg = Math.round(sum / avgs.length).toLocaleString()
    stats.median = Math.round(avgs[Math.floor(avgs.length / 2)]).toLocaleString()
  }
}

async function loadAnalysis(refresh: boolean) {
  try {
    await statsStore.fetchSalaryAnalysis(refresh)
  } catch {
    // 页面内显示错误提示。
  }
}

async function refreshAnalysis() {
  await loadAnalysis(true)
}

const topLocationOption = computed(() => {
  const d = salaryData.value
  if (!d.length) return null
  const sorted = [...d].sort((a, b) => b.avg - a.avg).slice(0, 15).reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 140, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: sorted.map((i) => i.location),
      axisLabel: { fontSize: 11, lineHeight: 14, width: 120, overflow: 'break' },
    },
    series: [{ type: 'bar', data: sorted.map((i) => i.avg), color: '#67C23A', barMaxWidth: 20 }],
  }
})

function contextArray(name: string) {
  const context = statsStore.salaryAnalysis?.context as Record<string, any> | undefined
  const value = context?.[name]
  return Array.isArray(value) ? value : []
}

function contextObject(name: string) {
  const context = statsStore.salaryAnalysis?.context as Record<string, any> | undefined
  const value = context?.[name]
  return value && typeof value === 'object' ? value : {}
}

function sectionKind(section: TechTrendSection) {
  const key = String(section.key || '')
  const title = String(section.title || '')
  if (key === 'salary_overview' || title.includes('总体')) return 'salary_overview'
  if (key === 'salary_location' || title.includes('地区')) return 'salary_location'
  if (key === 'salary_role' || title.includes('角色')) return 'salary_role'
  if (key === 'top_salary_jobs' || title.includes('高薪岗位')) return 'top_salary_jobs'
  return key
}

function chartItemsForSection(section: TechTrendSection) {
  const kind = sectionKind(section)
  if (kind === 'salary_overview') {
    const overview = contextObject('salary_overview')
    return [
      { name: '最低月薪', count: overview.min || 0 },
      { name: '中位月薪', count: overview.median || 0 },
      { name: '平均月薪', count: overview.avg || 0 },
      { name: '最高月薪', count: overview.max || 0 },
    ]
  }
  if (kind === 'salary_location') {
    return contextArray('salary_by_location')
      .map(item => ({ name: item.location, count: item.avg }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10)
  }
  if (kind === 'salary_role') {
    return contextArray('salary_by_role')
      .map(item => ({ name: item.role_name, count: item.salary_avg }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10)
  }
  if (kind === 'top_salary_jobs') {
    return contextArray('top_salary_jobs')
      .map(item => ({ name: item.title, count: item.salary_min }))
      .slice(0, 10)
  }
  return []
}

function wrapChartLabel(value: string) {
  const text = String(value || '')
  if (text.length <= 12) return text
  const chunks = text.match(/.{1,12}/g) || [text]
  return chunks.slice(0, 3).join('\n')
}

function analysisChartOption(section: TechTrendSection) {
  const items = [...chartItemsForSection(section)].reverse()
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value: number) => `HKD ${Math.round(value).toLocaleString()}`,
    },
    grid: { left: 220, right: 28, top: 12, bottom: 24 },
    xAxis: { type: 'value', axisLabel: { formatter: (value: number) => `${Math.round(value / 1000)}k` } },
    yAxis: {
      type: 'category',
      data: items.map(item => item.name),
      axisLabel: {
        fontSize: 11,
        lineHeight: 14,
        width: 190,
        overflow: 'break',
        formatter: wrapChartLabel,
      },
    },
    series: [{
      type: 'bar',
      data: items.map(item => item.count),
      color: '#409EFF',
      barMaxWidth: 20,
    }],
  }
}

function formatEvidence(item: string | Record<string, unknown>) {
  if (typeof item === 'string') return item
  const name = item.title || item.role_name || item.location || item.name || item.company
  const value = item.salary_avg || item.avg || item.salary_min || item.count
  return `${name || JSON.stringify(item)}${value ? `：HKD ${Number(value).toLocaleString()}` : ''}`
}
</script>

<style scoped>
.salary-page {
  padding-bottom: 24px;
}

.page-header,
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.page-header {
  margin-bottom: 16px;
}

.page-header h2,
.section-header h3 {
  margin: 0;
}

.analysis-section {
  margin-top: 24px;
}

.section-header {
  margin-bottom: 12px;
}

.analysis-col {
  margin-bottom: 16px;
}

.loading-state {
  display: grid;
  gap: 12px;
}

.analysis-card {
  min-height: 430px;
}

.analysis-chart {
  width: 100%;
  height: 260px;
  margin-bottom: 10px;
}

.summary {
  margin: 0 0 14px;
  color: #606266;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.evidence-list span {
  max-width: 100%;
  padding: 5px 8px;
  border-radius: 4px;
  background: #f5f7fa;
  color: #606266;
  font-size: 12px;
  line-height: 1.4;
  word-break: break-word;
}
</style>
