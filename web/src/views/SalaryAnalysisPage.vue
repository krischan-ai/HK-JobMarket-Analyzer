<template>
  <div>
    <h2 style="margin-top: 0">💰 薪資分析</h2>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-card shadow="hover"><div style="text-align:center"><div style="font-size:24px;font-weight:700;color:#409EFF">{{ stats.avg }}</div><div style="color:#909399">平均月薪 (HKD)</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div style="text-align:center"><div style="font-size:24px;font-weight:700;color:#67C23A">{{ stats.min }}</div><div style="color:#909399">最低月薪 (HKD)</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div style="text-align:center"><div style="font-size:24px;font-weight:700;color:#E6A23C">{{ stats.max }}</div><div style="color:#909399">最高月薪 (HKD)</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div style="text-align:center"><div style="font-size:24px;font-weight:700;color:#909399">{{ stats.median }}</div><div style="color:#909399">中位月薪 (HKD)</div></div></el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><strong>各區域薪資區間</strong></template>
          <v-chart :option="boxOption" autoresize style="height: 400px" v-if="boxOption" />
          <el-skeleton :rows="6" animated v-else />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><strong>Top 15 高薪崗位</strong></template>
          <v-chart :option="topJobOption" autoresize style="height: 400px" v-if="topJobOption" />
          <el-skeleton :rows="6" animated v-else />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref, reactive } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, BoxplotChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import api from '@/api'

use([CanvasRenderer, BarChart, BoxplotChart, GridComponent, TooltipComponent])

const stats = reactive({ avg: '-', min: '-', max: '-', median: '-' })
import type { SalaryDistribution } from '@/types'
const salaryData = ref<SalaryDistribution[]>([])

onMounted(async () => {
  const { data } = await api.get('/stats/salary-by-location')
  salaryData.value = data
  if (data.length) {
    const avgs = data.map((d: SalaryDistribution) => d.avg).sort((a: number, b: number) => a - b)
    stats.min = Math.round(avgs[0]).toLocaleString()
    stats.max = Math.round(avgs[avgs.length - 1]).toLocaleString()
    const sum = avgs.reduce((a: number, b: number) => a + b, 0)
    stats.avg = Math.round(sum / avgs.length).toLocaleString()
    stats.median = Math.round(avgs[Math.floor(avgs.length / 2)]).toLocaleString()
  }
})

const boxOption = computed(() => {
  const d = salaryData.value
  if (!d.length) return null
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: d.map(i => i.location), axisLabel: { fontSize: 10, rotate: 30 } },
    yAxis: { type: 'value', name: 'HKD' },
    series: [
      { type: 'bar', name: '最低', data: d.map(i => i.min), color: '#91cc75' },
      { type: 'bar', name: '平均', data: d.map(i => i.avg), color: '#409EFF' },
      { type: 'bar', name: '最高', data: d.map(i => i.max), color: '#ee6666' },
    ],
  }
})

const topJobOption = computed(() => {
  const d = salaryData.value
  if (!d.length) return null
  return { tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }, grid: { left: 80, right: 20, top: 10, bottom: 30 }, xAxis: { type: 'value' }, yAxis: { type: 'category', data: d.map(i => i.location), axisLabel: { fontSize: 11 } }, series: [{ type: 'bar', data: d.map(i => i.avg), color: '#67C23A', barMaxWidth: 20 }] }
})
</script>
