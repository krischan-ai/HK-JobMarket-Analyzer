<template>
  <div>
    <h2 style="margin-top: 0">區域分佈</h2>
    <el-card>
      <template #header><strong>各區域崗位數量</strong></template>
      <LocationBarChart :data="locationChartData" :height="500" />
    </el-card>
    <el-card style="margin-top: 16px">
      <template #header><strong>區域數據明細</strong></template>
      <DataTable :data="locationData" max-height="400">
        <el-table-column prop="location" label="區域" />
        <el-table-column prop="count" label="崗位數" sortable />
        <el-table-column prop="percentage" label="佔比" sortable>
          <template #default="{ row }">{{ (row.percentage * 100).toFixed(1) }}%</template>
        </el-table-column>
      </DataTable>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api'
import LocationBarChart from '@/components/charts/LocationBarChart.vue'
import DataTable from '@/components/common/DataTable.vue'
import type { LocationDistribution } from '@/types'

const locationData = ref<(LocationDistribution & { percentage: number })[]>([])
const total = ref(0)

onMounted(async () => {
  const { data } = await api.get('/stats/location-distribution')
  total.value = data.reduce((s: number, d: LocationDistribution) => s + d.count, 0)
  locationData.value = data.map((d: LocationDistribution) => ({ ...d, percentage: d.count / (total.value || 1) }))
})

const locationChartData = computed(() =>
  locationData.value.slice(0, 30).map((d) => ({ location: d.location, count: d.count }))
)
</script>
