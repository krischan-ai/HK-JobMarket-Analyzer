<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
  <el-empty description="暫無數據" :image-size="60" v-else-if="!loading" />
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
  loading?: boolean
}>(), {
  height: 400,
  loading: true,
})

function wrapAxisLabel(value: string) {
  const text = String(value || '')
  if (text.includes(',')) {
    return text.split(',').map(part => part.trim()).filter(Boolean).join('\n')
  }
  if (text.length <= 8) return text
  const chunks = text.match(/.{1,8}/g) || [text]
  return chunks.slice(0, 3).join('\n')
}

const option = computed(() => {
  if (!props.data.length) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 24, top: 20, bottom: 100, containLabel: true },
    dataZoom: props.data.length > 12 ? [
      { type: 'inside', start: 0, end: 60 },
      { type: 'slider', start: 0, end: 60, height: 18, bottom: 18 },
    ] : undefined,
    xAxis: {
      type: 'category',
      data: props.data.map((d) => d.label),
      axisLabel: {
        interval: 0,
        rotate: props.data.length > 8 ? 35 : 0,
        fontSize: 11,
        lineHeight: 14,
        hideOverlap: false,
        formatter: wrapAxisLabel,
      },
    },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}' } },
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
