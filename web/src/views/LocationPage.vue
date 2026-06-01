<template>
  <div>
    <h2 style="margin-top: 0">🗺️ 區域分佈</h2>
    <el-card>
      <template #header><strong>各區域崗位數量</strong></template>
      <v-chart :option="chartOption" autoresize style="height: 550px" v-if="chartOption" />
      <el-skeleton :rows="8" animated v-else />
    </el-card>
    <el-card style="margin-top: 16px">
      <template #header><strong>區域數據明細</strong></template>
      <el-table :data="locationData" style="width: 100%" max-height="400">
        <el-table-column prop="location" label="區域" />
        <el-table-column prop="count" label="崗位數" sortable />
        <el-table-column prop="percentage" label="佔比" sortable>
          <template #default="{ row }">{{ (row.percentage * 100).toFixed(1) }}%</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import api from '@/api'
import type { LocationDistribution } from '@/types'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const locationData = ref<(LocationDistribution & { percentage: number })[]>([])
const total = ref(0)

onMounted(async () => {
  const { data } = await api.get('/stats/location-distribution')
  total.value = data.reduce((s: number, d: LocationDistribution) => s + d.count, 0)
  locationData.value = data.map((d: LocationDistribution) => ({ ...d, percentage: d.count / (total.value || 1) }))
})

const chartOption = computed(() => {
  if (!locationData.value.length) return null
  const top30 = locationData.value.slice(0, 30).reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 100, right: 40, top: 10, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: top30.map(d => d.location), axisLabel: { fontSize: 11 } },
    series: [{ type: 'bar', data: top30.map(d => d.count), itemStyle: { color: '#409EFF' } }],
  }
})
</script>
