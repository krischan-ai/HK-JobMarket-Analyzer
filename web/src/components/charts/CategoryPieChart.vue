<template>
  <v-chart :option="option" autoresize :style="{ height: height + 'px' }" v-if="option" />
  <el-empty description="暫無數據" :image-size="60" v-else-if="!loading" />
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
  legend?: boolean
  loading?: boolean
}>(), {
  height: 350,
  radius: '62%',
  legend: true,
  loading: true,
})

function wrapLegend(value: string) {
  const text = String(value)
  if (text.length <= 12) return text
  const chunks = text.match(/.{1,12}/g) || [text]
  return chunks.slice(0, 2).join('\n')
}

const option = computed(() => {
  if (!props.data.length) return null
  return {
    tooltip: { trigger: 'item' },
    legend: props.legend ? {
      type: 'scroll',
      orient: 'vertical',
      right: 0,
      top: 'center',
      width: 150,
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 8,
      textStyle: { fontSize: 12, lineHeight: 16 },
      formatter: wrapLegend,
      pageIconSize: 12,
    } : undefined,
    series: [{
      type: 'pie',
      radius: props.radius,
      center: props.legend ? ['34%', '50%'] : ['50%', '50%'],
      data: props.data.map((c) => ({ name: c.category, value: c.count })),
      label: { show: false },
      emphasis: {
        label: {
          show: true,
          formatter: '{b}\n{c}',
          fontSize: 12,
          fontWeight: 'bold',
        },
      },
    }],
  }
})
</script>
