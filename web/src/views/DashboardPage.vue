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

    <el-divider style="margin: 24px 0 16px" />
    <h3 style="margin: 0 0 12px">角色分類分析</h3>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="24">
        <RoleSalaryChart :data="statsStore.roleSalary" />
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <LLMStatusCard
          :status="statsStore.llmStatus!"
          :classifying="statsStore.classifying"
          @run="handleRunClassification"
          v-if="statsStore.llmStatus"
        />
        <el-card v-else>
          <el-empty description="無法獲取 LLM 狀態" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="18">
        <RoleDistributionChart :data="statsStore.roleDistribution" />
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted } from 'vue'
import { useJobsStore } from '@/stores/jobs'
import { useStatsStore } from '@/stores/stats'
import { ElMessage } from 'element-plus'
import StatCards from '@/components/common/StatCards.vue'
import SkillBarChart from '@/components/charts/SkillBarChart.vue'
import SalaryBoxChart from '@/components/charts/SalaryBoxChart.vue'
import SourcePieChart from '@/components/charts/SourcePieChart.vue'
import CategoryPieChart from '@/components/charts/CategoryPieChart.vue'
import RoleDistributionChart from '@/components/RoleDistributionChart.vue'
import RoleSalaryChart from '@/components/RoleSalaryChart.vue'
import LLMStatusCard from '@/components/LLMStatusCard.vue'

const store = useJobsStore()
const statsStore = useStatsStore()

onMounted(() => {
  store.fetchDashboard()
  statsStore.fetchRoleDistribution()
  statsStore.fetchRoleSalary()
  statsStore.fetchLLMStatus()
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

async function handleRunClassification() {
  try {
    const result = await statsStore.runClassification()
    if (result) {
      ElMessage.success(result.message)
      await Promise.all([
        statsStore.fetchRoleDistribution(),
        statsStore.fetchRoleSalary(),
        statsStore.fetchLLMStatus(),
      ])
    }
  } catch {
    ElMessage.warning('分類請求失敗，請先在設置頁面配置 LLM')
  }
}
</script>
