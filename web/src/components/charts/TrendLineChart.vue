<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
  <el-skeleton :rows="6" animated v-else />
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

interface TrendItem {
  label: string
  value: number
}

const props = withDefaults(defineProps<{
  data: TrendItem[]
  height?: number
}>(), {
  height: 350,
})

const option = computed(() => {
  if (!props.data.length) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: props.data.map((d) => d.label) },
    yAxis: { type: 'value' },
    series: [{
      type: 'line',
      data: props.data.map((d) => d.value),
      smooth: true,
      color: '#409EFF',
      areaStyle: { opacity: 0.1 },
    }],
  }
})
</script>
