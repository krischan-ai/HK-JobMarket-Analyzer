<template>
  <el-card>
    <template #header><strong>角色分佈</strong></template>
    <v-chart :option="chartOption" autoresize style="height: 420px" v-if="data.length" />
    <el-empty description="暫無角色分類數據" v-else />
    <slot />
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
    right: 0,
    top: 'center',
    itemWidth: 12,
    itemHeight: 12,
    itemGap: 8,
    textStyle: { fontSize: 12 },
    pageIconSize: 12,
  },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      roseType: 'area',
      itemStyle: { borderRadius: 4 },
      data: props.data.map((d) => ({
        name: d.role_name,
        value: d.count,
      })),
      label: {
        show: false,
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold',
        },
      },
    },
  ],
}))
</script>
