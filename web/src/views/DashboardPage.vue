<template>
  <div>
    <h2 style="margin-top: 0">儀表盤</h2>

    <StatCards :cards="statCards" />

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="12">
        <el-card>
          <template #header><strong>技術棧需求排行 Top 15</strong></template>
          <SkillBarChart :data="store.dashboard?.top_skills || []" :loading="store.loading" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><strong>薪資分佈概覽</strong></template>
          <SalaryBoxChart :data="store.dashboard?.salary_by_location || []" :loading="store.loading" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><strong>數據來源佔比</strong></template>
          <SourcePieChart :data="store.dashboard?.source_distribution || []" :loading="store.loading" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><strong>技能類別分佈</strong></template>
          <CategoryPieChart :data="store.dashboard?.category_distribution || []" :loading="store.loading" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted } from 'vue'
import { useJobsStore } from '@/stores/jobs'
import StatCards from '@/components/common/StatCards.vue'
import SkillBarChart from '@/components/charts/SkillBarChart.vue'
import SalaryBoxChart from '@/components/charts/SalaryBoxChart.vue'
import SourcePieChart from '@/components/charts/SourcePieChart.vue'
import CategoryPieChart from '@/components/charts/CategoryPieChart.vue'

const store = useJobsStore()

onMounted(() => {
  store.fetchDashboard()
})

const statCards = computed(() => {
  const d = store.dashboard?.overview
  if (!d) return []
  return [
    { label: '崗位總數', value: d.total_jobs.toLocaleString() },
    { label: '公司數', value: d.total_companies.toLocaleString() },
    { label: '平均月薪 (HKD)', value: d.avg_salary.toLocaleString() },
    { label: '技能數', value: d.total_skills.toLocaleString() },
    { label: '數據來源', value: d.source_count },
    { label: '地區數', value: d.location_count },
  ]
})

</script>
