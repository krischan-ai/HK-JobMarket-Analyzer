<template>
  <div>
    <h2 style="margin-top: 0">薪資分析</h2>

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

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><strong>各區域薪資區間</strong></template>
          <SalaryBoxChart :data="salaryData" />
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
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import api from '@/api'
import StatCard from '@/components/common/StatCard.vue'
import SalaryBoxChart from '@/components/charts/SalaryBoxChart.vue'
import type { SalaryDistribution } from '@/types'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const stats = reactive({ avg: '-', min: '-', max: '-', median: '-' })
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

const topJobOption = computed(() => {
  const d = salaryData.value
  if (!d.length) return null
  const sorted = [...d].sort((a, b) => b.avg - a.avg).slice(0, 15)
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: sorted.map((i) => i.location), axisLabel: { fontSize: 11 } },
    series: [{ type: 'bar', data: sorted.map((i) => i.avg), color: '#67C23A', barMaxWidth: 20 }],
  }
})
</script>
