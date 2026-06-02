<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
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
  loading?: boolean
}>(), {
  height: 400,
})

const option = computed(() => {
  if (!props.data.length) return null
  const reversed = [...props.data].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 140, right: 20, top: 10, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: reversed.map((s) => s.skill),
      axisLabel: { fontSize: 12 },
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
