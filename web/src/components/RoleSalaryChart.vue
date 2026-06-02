<template>
  <el-card>
    <template #header><strong>各角色薪資對比</strong></template>
    <v-chart :option="chartOption" autoresize style="height: 350px" v-if="data.length" />
    <el-empty description="暫無角色薪資數據" v-else />
  </el-card>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TitleComponent, TooltipComponent } from 'echarts/components'
import type { RoleSalaryStats } from '@/types'

use([CanvasRenderer, BarChart, GridComponent, TitleComponent, TooltipComponent])

const props = defineProps<{
  data: RoleSalaryStats[]
}>()

const chartOption = computed(() => {
  const sorted = [...props.data].sort((a, b) => b.salary_avg - a.salary_avg)
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const d = params[0]
        return `${d.name}<br/>平均薪資: HKD ${d.value.toLocaleString()}`
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
</script>
