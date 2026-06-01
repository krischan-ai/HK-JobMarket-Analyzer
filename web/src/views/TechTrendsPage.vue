<template>
  <div>
    <h2 style="margin-top: 0">📈 技術趨勢分析</h2>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <strong>技術棧需求排行</strong>
              <el-slider v-model="topN" :min="5" :max="40" style="width: 200px" @change="fetchData" />
            </div>
          </template>
          <v-chart :option="barOption" autoresize style="height: 500px" v-if="barOption" />
          <el-skeleton :rows="8" animated v-else />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><strong>技能類別佔比</strong></template>
          <v-chart :option="pieOption" autoresize style="height: 350px" v-if="pieOption" />
          <el-skeleton :rows="6" animated v-else />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><strong>薪資趨勢</strong></template>
          <v-chart :option="salaryTrendOption" autoresize style="height: 350px" v-if="salaryTrendOption" />
          <el-skeleton :rows="6" animated v-else />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { useStatsStore } from '@/stores/stats'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart, LineChart } from 'echarts/charts'
import { GridComponent, TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, PieChart, LineChart, GridComponent, TitleComponent, TooltipComponent, LegendComponent])

const statsStore = useStatsStore()
const topN = ref(20)

onMounted(() => fetchData())

async function fetchData() {
  await Promise.all([
    statsStore.fetchTopSkills(topN.value),
    statsStore.fetchCategories(),
    statsStore.fetchSalaryByLocation(),
  ])
}

const barOption = computed(() => {
  if (!statsStore.topSkills.length) return null
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 140, right: 40, top: 10, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: statsStore.topSkills.map(s => s.skill).reverse(), axisLabel: { fontSize: 11 } },
    series: [{ type: 'bar', data: statsStore.topSkills.map(s => s.count).reverse(), itemStyle: { color: '#409EFF' }, barMaxWidth: 20 }],
  }
})

const pieOption = computed(() => {
  if (!statsStore.categories.length) return null
  return {
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: '65%', data: statsStore.categories.map(c => ({ name: c.category, value: c.count })), label: { formatter: '{b}: {d}%' } }],
  }
})

const salaryTrendOption = computed(() => {
  if (!statsStore.salaryByLocation.length) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: statsStore.salaryByLocation.map(d => d.location), axisLabel: { fontSize: 10, rotate: 30 } },
    yAxis: { type: 'value', name: 'HKD' },
    series: [{ type: 'line', name: '平均月薪', data: statsStore.salaryByLocation.map(d => d.avg), smooth: true, color: '#409EFF' }],
  }
})
</script>
