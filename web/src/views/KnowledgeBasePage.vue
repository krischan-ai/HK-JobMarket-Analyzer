<template>
  <div>
    <h2 style="margin-top: 0">知識庫總覽</h2>
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="8">
        <el-card>
          <template #header><strong>數據來源佔比</strong></template>
          <SourcePieChart :data="sourceData" :height="300" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><strong>技能熱度排行</strong></template>
          <SkillBarChart :data="skillData" :height="300" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><strong>版本歷史</strong></template>
          <DataTable :data="versions" max-height="250" :stripe="false">
            <el-table-column prop="version" label="版本" width="70" />
            <el-table-column prop="records" label="記錄數" width="70" />
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="date" label="日期" width="100" />
          </DataTable>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import api from '@/api'
import SourcePieChart from '@/components/charts/SourcePieChart.vue'
import SkillBarChart from '@/components/charts/SkillBarChart.vue'
import DataTable from '@/components/common/DataTable.vue'

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
</script>
