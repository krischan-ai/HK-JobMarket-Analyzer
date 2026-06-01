<template>
  <div>
    <h2 style="margin-top: 0">📊 儀表盤</h2>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="4" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 28px; font-weight: 700; color: #409EFF">{{ card.value }}</div>
            <div style="font-size: 13px; color: #909399; margin-top: 4px">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="12">
        <el-card>
          <template #header><strong>技術棧需求排行 Top 15</strong></template>
          <v-chart :option="skillsChartOption" autoresize style="height: 400px" v-if="skillsChartOption" />
          <el-skeleton :rows="6" animated v-else />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><strong>薪資分佈概覽</strong></template>
          <v-chart :option="salaryChartOption" autoresize style="height: 400px" v-if="salaryChartOption" />
          <el-skeleton :rows="6" animated v-else />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><strong>數據來源佔比</strong></template>
          <v-chart :option="sourceChartOption" autoresize style="height: 350px" v-if="sourceChartOption" />
          <el-skeleton :rows="6" animated v-else />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><strong>技能類別分佈</strong></template>
          <v-chart :option="categoryChartOption" autoresize style="height: 350px" v-if="categoryChartOption" />
          <el-skeleton :rows="6" animated v-else />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { useJobsStore } from '@/stores/jobs'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart, BoxplotChart } from 'echarts/charts'
import { GridComponent, TitleComponent, TooltipComponent, LegendComponent, DatasetComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, PieChart, BoxplotChart, GridComponent, TitleComponent, TooltipComponent, LegendComponent, DatasetComponent])

const store = useJobsStore()

onMounted(() => store.fetchDashboard())

const statCards = computed(() => {
  const d = store.dashboard?.overview
  if (!d) return []
  return [
    { label: '崗位總數', value: d.total_jobs.toLocaleString() },
    { label: '公司數', value: d.total_companies.toLocaleString() },
    { label: '平均月薪 (HKD)', value: d.avg_salary.toLocaleString() },
    { label: '技能數', value: d.total_skills.toLocaleString() },
    { label: '數據來源', value: d.source_count },
    { label: '地區數', value: d.location_count },
  ]
})

const skillsChartOption = computed(() => {
  const skills = store.dashboard?.top_skills || []
  if (!skills.length) return null
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 140, right: 20, top: 10, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: skills.map(s => s.skill).reverse(), axisLabel: { fontSize: 12 } },
    series: [{ type: 'bar', data: skills.map(s => s.count).reverse(), color: '#409EFF', barMaxWidth: 24 }],
  }
})

const salaryChartOption = computed(() => {
  const data = store.dashboard?.salary_by_location || []
  if (!data.length) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: data.map(d => d.location), axisLabel: { fontSize: 10, rotate: 30 } },
    yAxis: { type: 'value', name: 'HKD' },
    series: [
      { type: 'bar', name: '最低', data: data.map(d => d.min), color: '#91cc75' },
      { type: 'bar', name: '平均', data: data.map(d => d.avg), color: '#409EFF' },
      { type: 'bar', name: '最高', data: data.map(d => d.max), color: '#ee6666' },
    ],
  }
})

const sourceChartOption = computed(() => {
  const sources = store.dashboard?.source_distribution || []
  if (!sources.length) return null
  return {
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: ['40%', '70%'], data: sources.map(s => ({ name: s.source, value: s.count })), label: { formatter: '{b}: {d}%' } }],
  }
})

const categoryChartOption = computed(() => {
  const cats = store.dashboard?.category_distribution || []
  if (!cats.length) return null
  return {
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: '65%', data: cats.map(c => ({ name: c.category, value: c.count })), label: { formatter: '{b}: {c}' } }],
  }
})
</script>
