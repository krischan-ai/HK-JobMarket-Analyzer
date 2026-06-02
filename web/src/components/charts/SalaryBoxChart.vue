<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
  <el-skeleton :rows="6" animated v-else />
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

interface SalaryItem {
  location: string
  min: number
  avg: number
  max: number
}

const props = withDefaults(defineProps<{
  data: SalaryItem[]
  height?: number
}>(), {
  height: 400,
})

const option = computed(() => {
  if (!props.data.length) return null
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'category',
      data: props.data.map((d) => d.location),
      axisLabel: { fontSize: 10, rotate: 30 },
    },
    yAxis: { type: 'value', name: 'HKD' },
    series: [
      { type: 'bar', name: '最低', data: props.data.map((d) => d.min), color: '#91cc75' },
      { type: 'bar', name: '平均', data: props.data.map((d) => d.avg), color: '#409EFF' },
      { type: 'bar', name: '最高', data: props.data.map((d) => d.max), color: '#ee6666' },
    ],
  }
})
</script>
