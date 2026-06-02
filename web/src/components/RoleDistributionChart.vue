<template>
  <el-card>
    <template #header><strong>角色分佈</strong></template>
    <v-chart :option="chartOption" autoresize style="height: 350px" v-if="data.length" />
    <el-empty description="暫無角色分類數據" v-else />
  </el-card>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import type { RoleDistribution } from '@/types'

use([CanvasRenderer, PieChart, TitleComponent, TooltipComponent, LegendComponent])

const props = defineProps<{
  data: RoleDistribution[]
}>()

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)',
  },
  legend: {
    type: 'scroll',
    orient: 'vertical',
    right: 10,
    top: 20,
    bottom: 20,
    itemGap: 6,
  },
  series: [
    {
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['38%', '50%'],
      roseType: 'area',
      itemStyle: { borderRadius: 4 },
      data: props.data.map((d) => ({
        name: d.role_name,
        value: d.count,
      })),
      label: {
        formatter: '{b}\n{d}%',
        fontSize: 10,
      },
    },
  ],
}))
</script>
