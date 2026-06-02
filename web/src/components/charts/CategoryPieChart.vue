<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
  <el-skeleton :rows="6" animated v-else />
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

interface CatItem {
  category: string
  count: number
}

const props = withDefaults(defineProps<{
  data: CatItem[]
  height?: number
  radius?: string
}>(), {
  height: 350,
  radius: '65%',
})

const option = computed(() => {
  if (!props.data.length) return null
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: props.radius,
      data: props.data.map((c) => ({ name: c.category, value: c.count })),
      label: { formatter: '{b}: {c}' },
    }],
  }
})
</script>
