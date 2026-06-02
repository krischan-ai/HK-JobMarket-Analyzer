<template>
  <div>
    <h2 style="margin-top: 0">技術趨勢分析</h2>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <strong>技術棧需求排行</strong>
              <el-slider v-model="topN" :min="5" :max="40" style="width: 200px" @change="fetchData" />
            </div>
          </template>
          <SkillBarChart :data="statsStore.topSkills" :height="500" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><strong>技能類別佔比</strong></template>
          <CategoryPieChart :data="statsStore.categories" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><strong>薪資趨勢</strong></template>
          <TrendLineChart
            :data="statsStore.salaryByLocation.map(d => ({ label: d.location, value: d.avg }))"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import { useStatsStore } from '@/stores/stats'
import SkillBarChart from '@/components/charts/SkillBarChart.vue'
import CategoryPieChart from '@/components/charts/CategoryPieChart.vue'
import TrendLineChart from '@/components/charts/TrendLineChart.vue'

const statsStore = useStatsStore()
const topN = ref(20)

onMounted(() => fetchData())

async function fetchData() {
  await Promise.all([
    statsStore.fetchTopSkills(topN.value),
    statsStore.fetchCategories(),
    statsStore.fetchSalaryByLocation(),
  ])
}
</script>
