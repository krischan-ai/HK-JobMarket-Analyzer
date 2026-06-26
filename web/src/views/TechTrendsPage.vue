<template>
  <div class="tech-trends-page">
    <div class="page-header">
      <div>
        <h2>技术趋势分析</h2>
        <p>技能榜单、角色分类、软技能需求和知识库智能总结。</p>
      </div>
      <div class="header-actions">
        <el-tag :type="analysisStatus.type">{{ analysisStatus.text }}</el-tag>
        <el-button :loading="statsStore.techTrendLoading" type="primary" @click="refreshAnalysis">
          重新生成分析
        </el-button>
      </div>
    </div>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <el-card>
          <template #header><strong>技术栈需求榜单</strong></template>
          <el-table :data="pagedSkills" stripe>
            <el-table-column label="排名" width="80">
              <template #default="{ $index }">{{ (skillPage - 1) * pageSize + $index + 1 }}</template>
            </el-table-column>
            <el-table-column prop="skill" label="技术栈" min-width="280">
              <template #default="{ row }"><span class="skill-name">{{ row.skill }}</span></template>
            </el-table-column>
            <el-table-column prop="category" label="类别" min-width="180">
              <template #default="{ row }">{{ categoryName(row.category) }}</template>
            </el-table-column>
            <el-table-column prop="count" label="提及次数" width="120" sortable />
          </el-table>
          <div class="pager-row">
            <el-pagination
              v-model:current-page="skillPage"
              :page-size="pageSize"
              layout="prev, pager, next"
              :total="statsStore.topSkills.length"
            />
          </div>
          <AnalysisSummary
            :section="findSection('tech_stack_demand')"
            :loading="statsStore.techTrendLoading"
            :error="statsStore.techTrendError"
            fallback-title="技术栈需求分析"
            :total-jobs="totalJobs"
          />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <el-card>
          <template #header><strong>细分技能类别占比</strong></template>
          <CategoryPieChart :data="statsStore.categories" :height="430" />
          <AnalysisSummary
            :section="findSection('tech_category')"
            :loading="statsStore.techTrendLoading"
            :error="statsStore.techTrendError"
            fallback-title="细分技能类别分析"
            :total-jobs="totalJobs"
          />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <LLMStatusCard
          v-if="statsStore.llmStatus"
          :status="statsStore.llmStatus"
          :classifying="statsStore.classifying"
          @run="handleRunClassification"
        />
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <RoleDistributionChart :data="statsStore.roleDistribution">
          <AnalysisSummary
            :section="findSection('role_distribution')"
            :loading="statsStore.techTrendLoading"
            :error="statsStore.techTrendError"
            fallback-title="角色分布分析"
            :total-jobs="totalJobs"
          />
        </RoleDistributionChart>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <el-card>
          <template #header><strong>角色分类分析</strong></template>
          <v-chart
            v-if="findSection('role_classification')"
            class="analysis-chart"
            :option="analysisChartOption(findSection('role_classification')!)"
            autoresize
          />
          <AnalysisSummary
            :section="findSection('role_classification')"
            :loading="statsStore.techTrendLoading"
            :error="statsStore.techTrendError"
            fallback-title="角色分类分析"
            :total-jobs="totalJobs"
          />
        </el-card>
      </el-col>
    </el-row>

    <section class="analysis-section">
      <div class="section-header">
        <h3>知识库智能总结</h3>
        <el-tag :type="analysisStatus.type">{{ analysisStatus.text }}</el-tag>
      </div>

      <el-alert
        v-if="statsStore.techTrendError"
        :title="statsStore.techTrendError"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 16px"
      />
      <el-alert
        v-else-if="statsStore.techTrendAnalysis?.warning"
        :title="statsStore.techTrendAnalysis.warning"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 16px"
      />

      <div v-if="statsStore.techTrendLoading" class="loading-state">
        <el-alert title="AI 正在调用岗位知识库并生成分析，通常需要几十秒。已有结果会在原始数据不变时走缓存。" type="info" show-icon :closable="false" />
        <el-skeleton :rows="8" animated />
      </div>
      <el-row v-else :gutter="16">
        <el-col
          v-for="section in knowledgeSections"
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
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElAlert, ElMessage, ElSkeleton } from 'element-plus'
import VChart from 'vue-echarts'
import { useStatsStore } from '@/stores/stats'
import CategoryPieChart from '@/components/charts/CategoryPieChart.vue'
import RoleDistributionChart from '@/components/RoleDistributionChart.vue'
import LLMStatusCard from '@/components/LLMStatusCard.vue'
import type { TechTrendSection } from '@/types'

const statsStore = useStatsStore()
const pageSize = 20
const skillPage = ref(1)

onMounted(() => {
  void Promise.all([
    statsStore.fetchTopSkills(500),
    statsStore.fetchCategories(),
    statsStore.fetchRoleDistribution(),
    statsStore.fetchLLMStatus(),
  ])
  void loadAnalysis(false)
})

onBeforeUnmount(() => {
  statsStore.cancelTechTrendAnalysis()
})

const totalJobs = computed(() => Number((statsStore.techTrendAnalysis?.context as Record<string, unknown> | undefined)?.total_jobs || 0))

const pagedSkills = computed(() => {
  const start = (skillPage.value - 1) * pageSize
  return statsStore.topSkills.slice(start, start + pageSize)
})

const knowledgeSections = computed(() => {
  const sections = statsStore.techTrendAnalysis?.sections || []
  return sections.filter(section => ['soft_skill_demand', 'responsibility', 'company_industry', 'tech_direction'].includes(sectionKind(section)))
})

const analysisStatus = computed(() => {
  if (statsStore.techTrendLoading) return { text: 'AI 分析中', type: 'warning' as const }
  if (!statsStore.techTrendAnalysis) return { text: '待生成', type: 'info' as const }
  if (statsStore.techTrendAnalysis.from_cache || statsStore.techTrendAnalysis.analysis_status === 'cached') {
    return { text: '使用缓存', type: 'success' as const }
  }
  if (statsStore.techTrendAnalysis.llm_used) return { text: 'LLM 已完成', type: 'success' as const }
  return { text: '本地兜底摘要', type: 'warning' as const }
})

async function loadAnalysis(refresh: boolean) {
  try {
    await statsStore.fetchTechTrendAnalysis(refresh)
  } catch {
    // 页面内已显示错误提示。
  }
}

async function refreshAnalysis() {
  await loadAnalysis(true)
}

async function handleRunClassification() {
  try {
    const result = await statsStore.runClassification()
    if (result) {
      ElMessage.success(result.message)
      await Promise.all([
        statsStore.fetchRoleDistribution(),
        statsStore.fetchLLMStatus(),
        loadAnalysis(true),
      ])
    }
  } catch {
    ElMessage.warning('分类请求失败，请先在设置页配置 LLM')
  }
}

function findSection(kind: string) {
  const sections = statsStore.techTrendAnalysis?.sections || []
  return sections.find(section => sectionKind(section) === kind)
}

function sectionKind(section: { key?: string; title?: string }) {
  const key = String(section.key || '')
  const title = String(section.title || '')
  if (key.includes('tech_stack') || title.includes('技术栈')) return 'tech_stack_demand'
  if (key.includes('skill_category') || title.includes('技能类别') || title.includes('细分')) return 'tech_category'
  if (key.includes('role_distribution') || title.includes('角色分布')) return 'role_distribution'
  if (key.includes('role') || title.includes('角色分类')) return 'role_classification'
  if (key.includes('soft_skill') || title.includes('软技能')) return 'soft_skill_demand'
  if (key.includes('responsibility') || title.includes('岗位职责')) return 'responsibility'
  if (key.includes('company') || title.includes('公司') || title.includes('行业')) return 'company_industry'
  if (key.includes('tech_direction') || title.includes('技术方向')) return 'tech_direction'
  return key
}

function categoryName(category?: string) {
  const map: Record<string, string> = {
    programming_languages: '编程语言',
    frameworks_libraries: '框架与开发库',
    cloud_devops: '云平台与 DevOps',
    databases: '数据库与数据存储',
    ai_concepts: 'AI 概念与方法',
  }
  return map[category || ''] || category || '-'
}

function contextArray(name: string) {
  const context = statsStore.techTrendAnalysis?.context as Record<string, any> | undefined
  const value = context?.[name]
  return Array.isArray(value) ? value : []
}

function chartItemsForSection(section: TechTrendSection) {
  const kind = sectionKind(section)
  const evidenceItems = (section.evidence || [])
    .filter(item => typeof item !== 'string')
    .map((item: any) => ({
      name: item.name || item.role_name || item.skill || item.category || item.title || item.company || item.location,
      count: item.count || item.percentage || item.value || item.avg || item.salary_avg || 0,
    }))
    .filter(item => item.name && item.count)
  if (kind === 'soft_skill_demand') {
    const items = contextArray('soft_skill_demand').map(item => ({ name: item.name, count: item.count })).slice(0, 12)
    return items.length ? items : evidenceItems.slice(0, 12)
  }
  if (kind === 'responsibility') {
    const items = contextArray('responsibility_distribution').slice(0, 10)
    return items.length ? items : evidenceItems.slice(0, 10)
  }
  if (kind === 'company_industry') {
    const industries = contextArray('industry_distribution')
    const items = industries.slice(0, 10)
    return items.length ? items : evidenceItems.slice(0, 10)
  }
  if (kind === 'tech_direction') {
    const items = contextArray('tech_stack_ranking').map(item => ({ name: item.skill || item.name, count: item.count })).slice(0, 10)
    return items.length ? items : evidenceItems.slice(0, 10)
  }
  return evidenceItems.slice(0, 10)
}

function wrapChartLabel(value: string) {
  const text = String(value || '')
  if (text.length <= 12) return text
  const chunks = text.match(/.{1,12}/g) || [text]
  return chunks.slice(0, 4).join('\n')
}

function analysisChartOption(section: TechTrendSection) {
  const items = [...chartItemsForSection(section)].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 240, right: 28, top: 12, bottom: 24 },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: items.map(item => item.name),
      axisLabel: {
        fontSize: 11,
        lineHeight: 14,
        width: 210,
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
  const name = item.skill || item.name || item.category || item.role_name || item.title
  const count = item.count || item.percentage
  const suffix = item.percentage ? '%' : ''
  return `${name || JSON.stringify(item)}${count ? `：${count}${suffix}` : ''}`
}

const AnalysisSummary = defineComponent({
  name: 'AnalysisSummary',
  props: {
    section: Object,
    loading: Boolean,
    error: String,
    fallbackTitle: String,
    totalJobs: Number,
  },
  setup(props) {
    return () => h('div', { class: 'inline-summary' }, [
      props.loading
        ? h(ElSkeleton, { rows: 4, animated: true })
        : props.error
          ? h(ElAlert, { title: props.error, type: 'warning', showIcon: true, closable: false })
          : props.section
            ? h('div', { class: 'summary-body' }, [
              h('h4', { class: 'summary-title' }, props.section.title || props.fallbackTitle),
              props.totalJobs ? h('div', { class: 'summary-meta' }, [
                h('span', '知识库岗位数：' + props.totalJobs),
              ]) : null,
              h('p', { class: 'summary-text' }, props.section.summary),
              props.section.evidence?.length
                ? h('div', { class: 'evidence-list' }, props.section.evidence.slice(0, 8).map((item: string | Record<string, unknown>, idx: number) =>
                  h('span', { key: idx }, formatEvidence(item)),
                ))
                : null,
            ])
            : h('p', { class: 'summary-text' }, `${props.fallbackTitle || '分析'}暂无数据`),
    ])
  },
})
</script>

<style scoped>
.tech-trends-page {
  padding-bottom: 32px;
}

.page-header,
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.page-header h2,
.section-header h3 {
  margin: 0;
}

.page-header p {
  margin: 6px 0 0;
  color: #606266;
  font-size: 14px;
}

.skill-name {
  display: inline-block;
  max-width: 100%;
  font-size: 13px;
  line-height: 1.45;
  word-break: break-word;
}

.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.inline-summary {
  margin-top: 16px;
  padding: 14px 0 0;
  border-top: 1px solid #ebeef5;
}

.summary-title {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.45;
  font-weight: 600;
}

.summary-text,
.summary {
  margin: 0 0 12px;
  color: #606266;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.analysis-section {
  margin-top: 24px;
}

.analysis-col {
  margin-bottom: 16px;
}

.loading-state {
  display: grid;
  gap: 12px;
}

.analysis-card {
  min-height: auto;
}

.analysis-chart {
  width: 100%;
  height: 280px;
  margin-bottom: 12px;
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
}

:deep(.inline-summary .summary-title) {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.45;
  font-weight: 600;
}

:deep(.inline-summary .summary-text) {
  margin: 0 0 12px;
  color: #606266;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
}

:deep(.inline-summary .summary-meta),
:deep(.inline-summary .evidence-list) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.inline-summary .summary-meta) {
  margin-bottom: 12px;
}

:deep(.inline-summary .summary-meta span),
:deep(.inline-summary .evidence-list span) {
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
