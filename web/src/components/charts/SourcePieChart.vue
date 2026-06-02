<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
  <el-skeleton :rows="6" animated v-else />
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

interface SourceItem {
  source: string
  count: number
}

const props = withDefaults(defineProps<{
  data: SourceItem[]
  height?: number
}>(), {
  height: 350,
})

const option = computed(() => {
  if (!props.data.length) return null
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: props.data.map((s) => ({ name: s.source, value: s.count })),
      label: { formatter: '{b}: {d}%' },
    }],
  }
})
</script>
