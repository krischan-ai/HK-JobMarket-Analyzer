<template>
  <div class="salary-page">
    <div class="page-header">
      <h2>薪資分析</h2>
      <div class="header-actions">
        <span :key="`header-${analysisRenderKey}`" class="status-pill" :class="`status-pill--${analysisStatusType}`">
          {{ analysisStatusText }}
        </span>
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


    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <el-card>
          <template #header><strong>各角色薪資對比</strong></template>
          <v-chart :option="roleSalaryChartOption" autoresize style="height: 350px" v-if="statsStore.roleSalary.length" />
          <el-empty description="暫無角色薪資數據" v-else />
          <template v-if="roleSalarySectionData">
            <div class="role-salary-summary">
              <h4 class="summary-title">{{ roleSalarySectionData.title }}</h4>
              <div class="summary-meta">
                <span>知识库岗位数：{{ statsStore.salaryAnalysis?.context?.total_jobs || 0 }}</span>
              </div>
              <p class="summary">{{ roleSalarySectionData.summary }}</p>
              <div v-if="salaryEvidenceLabels(roleSalarySectionData).length" class="evidence-list">
                <span v-for="(label, idx) in salaryEvidenceLabels(roleSalarySectionData)" :key="idx">{{ label }}</span>
              </div>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>    <section :key="`analysis-${analysisRenderKey}`" class="analysis-section">
      <div class="section-header">
        <h3>薪资智能总结</h3>
        <span :key="`section-${analysisRenderKey}`" class="status-pill" :class="`status-pill--${analysisStatusType}`">
          {{ analysisStatusText }}
        </span>
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

      <div v-if="showAnalysisLoading" class="loading-state">
        <el-alert title="AI 正在调用薪资知识库并生成分析。原始数据不变时后续会直接使用缓存。" type="info" show-icon :closable="false" />
        <el-skeleton :rows="8" animated />
      </div>
      <el-row v-show="!isAnalysisLoading()" :gutter="16">
        <el-col
          v-for="section in visibleSalarySections"
          :key="section.key || section.title"
          :span="24"
          class="analysis-col"
        >
          <el-card class="analysis-card">
            <template #header><strong>{{ section.title }}</strong></template>
            <v-chart class="analysis-chart" :option="analysisChartOption(section)" autoresize />
            <p class="summary">{{ section.summary }}</p>
            <div v-if="salaryEvidenceLabels(section).length" class="evidence-list">
              <span v-for="(label, idx) in salaryEvidenceLabels(section)" :key="idx">
                {{ label }}
              </span>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </section>
  </div>
</template>

<script lang="ts" setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
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
const analysisRenderKey = ref(0)
const visibleSalarySections = reactive<TechTrendSection[]>([])
const roleSalarySectionData = ref<TechTrendSection | null>(null)
const showAnalysisLoading = computed(() => statsStore.salaryAnalysisLoading && !statsStore.salaryAnalysis)

const analysisStatus = computed(() => {
  if (showAnalysisLoading.value) return { text: 'AI 分析中', type: 'warning' as const }
  if (!statsStore.salaryAnalysis) return { text: '待生成', type: 'info' as const }
  if (statsStore.salaryAnalysis.from_cache || statsStore.salaryAnalysis.analysis_status === 'cached') {
    return { text: '使用缓存', type: 'success' as const }
  }
  if (statsStore.salaryAnalysis.llm_used) return { text: 'LLM 已完成', type: 'success' as const }
  return { text: '本地兜底摘要', type: 'warning' as const }
})

const analysisStatusText = computed(() => analysisStatus.value.text)
const analysisStatusType = computed(() => analysisStatus.value.type)

onMounted(() => {
  statsStore.cancelSalaryAnalysis()
  void Promise.all([
    loadSalaryData(),
    statsStore.fetchRoleSalary(),
  ])
  void loadAnalysis(false)
})

onBeforeUnmount(() => {
  statsStore.cancelSalaryAnalysis()
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
  } finally {
    syncSalarySections()
    analysisRenderKey.value += 1
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

const roleSalaryChartOption = computed(() => {
  const sorted = [...statsStore.roleSalary].sort((a, b) => b.salary_avg - a.salary_avg)
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const d = params[0]
        return `${d.name}<br/>平均薪資: HKD ${Number(d.value).toLocaleString()}`
      },
    },
    grid: { left: 140, right: 40, top: 10, bottom: 20 },
    xAxis: { type: 'value', name: 'HKD / 月' },
    yAxis: {
      type: 'category',
      data: sorted.map((d) => d.role_name),
      axisLabel: { fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: sorted.map((d) => ({
          name: d.role_name,
          value: d.salary_avg,
          itemStyle: { borderRadius: [0, 4, 4, 0] },
        })),
        barMaxWidth: 28,
      },
    ],
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

function isAnalysisLoading() {
  return statsStore.salaryAnalysisLoading && !statsStore.salaryAnalysis
}

function getSalarySummarySections() {
  return (statsStore.salaryAnalysis?.sections || []).filter(section => sectionKind(section) !== 'salary_role')
}

function getRoleSalarySection() {
  return (statsStore.salaryAnalysis?.sections || []).find(section => sectionKind(section) === 'salary_role')
}

function syncSalarySections() {
  visibleSalarySections.splice(0, visibleSalarySections.length, ...getSalarySummarySections())
  roleSalarySectionData.value = getRoleSalarySection() || null
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
      .map(item => ({ name: item.display_name || item.role_name || item.title, count: item.salary_min }))
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

function salaryEvidenceLabels(section?: TechTrendSection) {
  if (!section) return []
  const raw: unknown = section.evidence
  // LLM 返回的 evidence 可能是数组，也可能是一整段字符串；统一成数组再渲染，避免对字符串调用 .map 抛错导致整块消失。
  const list: Array<string | Record<string, unknown>> = Array.isArray(raw)
    ? raw
    : typeof raw === 'string'
      ? raw.split(/[、；;\n]+/).map((part: string) => part.trim()).filter(Boolean)
      : []
  return list
    .slice(0, 8)
    .map(item => formatEvidence(item, sectionKind(section)))
    .filter(Boolean)
}

function formatEvidence(item: string | Record<string, unknown>, kind = '') {
  if (typeof item === 'string') return item
  if (kind === 'salary_overview') {
    const count = Number(item.count || 0)
    const avg = Number(item.avg || 0)
    return count || avg ? '样本数 ' + count + '，平均 HKD ' + avg.toLocaleString() : ''
  }
  if (kind === 'top_salary_jobs') {
    const title = String(item.title || '')
    const industry = String(item.industry_category || '')
    const role = String(item.role_name || '')
    const location = String(item.location || '')
    const salary = Number(item.salary_min || 0)
    return [
      title,
      industry,
      role,
      location,
      salary ? 'HKD ' + salary.toLocaleString() : '',
    ].filter(Boolean).join(' | ')
  }
  const name = String(item.role_name || item.location || item.name || item.company || item.title || '')
  const value = Number(item.salary_avg || item.avg || item.salary_min || item.count || 0)
  if (!name) return ''
  return name + (value ? '：HKD ' + value.toLocaleString() : '')
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

.status-pill {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 9px;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 12px;
  line-height: 22px;
  white-space: nowrap;
}

.status-pill--success {
  color: #529b2e;
  background: #f0f9eb;
  border-color: #e1f3d8;
}

.status-pill--warning {
  color: #b88230;
  background: #fdf6ec;
  border-color: #faecd8;
}

.status-pill--info {
  color: #73767a;
  background: #f4f4f5;
  border-color: #e9e9eb;
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

.summary-title {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.45;
  font-weight: 600;
}

.role-salary-summary {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid #ebeef5;
}

.summary {
  margin: 0 0 14px;
  color: #606266;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.summary-meta,
.evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-meta span,
.evidence-list span {
  max-width: 100%;
  padding: 5px 8px;
  border-radius: 4px;
  background: #f5f7fa;
  color: #606266;
  font-size: 12px;
  line-height: 1.4;
  word-break: break-word;
  overflow-wrap: anywhere;
}
</style>
