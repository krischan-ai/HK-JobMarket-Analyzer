<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
  <el-empty description="暫無數據" :image-size="60" v-else-if="!loading" />
  <el-skeleton :rows="6" animated v-else />
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

interface SkillItem {
  skill: string
  count: number
}

const props = withDefaults(defineProps<{
  data: SkillItem[]
  height?: number
  left?: number
  loading?: boolean
}>(), {
  height: 400,
  left: 220,
})

function wrapLabel(value: string) {
  const text = String(value)
  if (text.length <= 14) return text
  const chunks = text.match(/.{1,14}/g) || [text]
  return chunks.slice(0, 3).join('\n')
}

const option = computed(() => {
  if (!props.data.length) return null
  const reversed = [...props.data].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: props.left, right: 28, top: 10, bottom: 24, containLabel: false },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: reversed.map((s) => s.skill),
      axisLabel: {
        fontSize: 11,
        lineHeight: 14,
        width: props.left - 28,
        overflow: 'break',
        formatter: wrapLabel,
      },
    },
    series: [{
      type: 'bar',
      data: reversed.map((s) => s.count),
      color: '#409EFF',
      barMaxWidth: 24,
    }],
  }
})
</script>
