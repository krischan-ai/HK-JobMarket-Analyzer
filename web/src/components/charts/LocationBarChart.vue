<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
  <el-skeleton :rows="6" animated v-else />
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

interface LocationItem {
  location: string
  count: number
}

const props = withDefaults(defineProps<{
  data: LocationItem[]
  height?: number
  horizontal?: boolean
}>(), {
  height: 400,
  horizontal: true,
})

const option = computed(() => {
  if (!props.data.length) return null
  const items = [...props.data].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 100, right: 40, top: 10, bottom: 20 },
    yAxis: { type: 'category', data: items.map((d) => d.location), axisLabel: { fontSize: 11 } },
    xAxis: { type: 'value' },
    series: [{ type: 'bar', data: items.map((d) => d.count), itemStyle: { color: '#409EFF' } }],
  }
})
</script>
