<template>
  <div>
    <h2 style="margin-top: 0">📚 知識庫總覽</h2>
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="8">
        <el-card>
          <template #header><strong>數據來源佔比</strong></template>
          <v-chart :option="sourceOption" autoresize style="height: 300px" v-if="sourceOption" />
          <el-skeleton :rows="5" animated v-else />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><strong>技能熱度排行</strong></template>
          <v-chart :option="skillOption" autoresize style="height: 300px" v-if="skillOption" />
          <el-skeleton :rows="5" animated v-else />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><strong>版本歷史</strong></template>
          <el-table :data="versions" size="small" max-height="250">
            <el-table-column prop="version" label="版本" width="70" />
            <el-table-column prop="records" label="記錄數" width="70" />
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="date" label="日期" width="100" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import api from '@/api'

use([CanvasRenderer, BarChart, PieChart, GridComponent, TooltipComponent])

const sourceData = ref<{ source: string; count: number }[]>([])
const skillData = ref<{ skill: string; count: number }[]>([])
const versions = ref<{ version: string; records: string; description: string; date: string }[]>([])

onMounted(async () => {
  const [sr, sk, vr] = await Promise.all([
    api.get('/stats/source-distribution'),
    api.get('/knowledge/skill-frequency', { params: { top_n: 15 } }),
    api.get('/knowledge/versions'),
  ])
  sourceData.value = sr.data
  skillData.value = sk.data
  versions.value = vr.data
})

const sourceOption = computed(() => sourceData.value.length ? { tooltip: { trigger: 'item' }, series: [{ type: 'pie', radius: '65%', data: sourceData.value.map(s => ({ name: s.source, value: s.count })) }] } : null)
const skillOption = computed(() => skillData.value.length ? { tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }, grid: { left: 100, right: 20, top: 10, bottom: 20 }, xAxis: { type: 'value' }, yAxis: { type: 'category', data: skillData.value.map(s => s.skill).reverse(), axisLabel: { fontSize: 10 } }, series: [{ type: 'bar', data: skillData.value.map(s => s.count).reverse(), color: '#409EFF' }] } : null)
</script>
