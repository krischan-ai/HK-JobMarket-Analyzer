<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
  <el-empty description="暫無數據" :image-size="60" v-else-if="!loading" />
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
  loading?: boolean
}>(), {
  height: 350,
  loading: true,
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
