<template>
  <div>
    <h2 style="margin-top: 0">數據管理</h2>
    <el-card>
      <el-form :inline="true" style="margin-bottom: 16px">
        <el-form-item label="搜索">
          <el-input v-model="keyword" placeholder="關鍵詞" clearable @change="search" style="width: 200px" />
        </el-form-item>
        <el-form-item label="地點">
          <el-input v-model="location" placeholder="地點" clearable @change="search" style="width: 150px" />
        </el-form-item>
        <el-form-item label="來源">
          <el-select v-model="source" clearable @change="search" style="width: 130px">
            <el-option v-for="s in sources" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <DataTable
        :data="jobs"
        :loading="loading"
        :show-pagination="true"
        :page="currentPage"
        :size="pageSize"
        :total="total"
        max-height="500"
        @page-change="onPageChange"
      >
        <el-table-column prop="job_id" label="Job ID" width="150" />
        <el-table-column prop="title" label="崗位名稱" min-width="180" />
        <el-table-column prop="company" label="公司" width="150" />
        <el-table-column prop="location" label="地點" width="110" />
        <el-table-column prop="source" label="來源" width="100">
          <template #default="{ row }"><el-tag size="small">{{ row.source }}</el-tag></template>
        </el-table-column>
        <el-table-column label="月薪" width="150">
          <template #default="{ row }">{{ row.salary_min ? `HK$${row.salary_min.toLocaleString()}` : '-' }}</template>
        </el-table-column>
      </DataTable>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import api from '@/api'
import DataTable from '@/components/common/DataTable.vue'
import type { JobItem } from '@/types'

const jobs = ref<JobItem[]>([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const location = ref('')
const source = ref('')
const sources = ref<string[]>([])

onMounted(async () => {
  const { data } = await api.get('/jobs/sources')
  sources.value = data
  search()
})

async function search() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: currentPage.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (location.value) params.location = location.value
    if (source.value) params.source = source.value
    const { data } = await api.get('/jobs', { params })
    jobs.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function reset() {
  keyword.value = ''
  location.value = ''
  source.value = ''
  currentPage.value = 1
  search()
}

function onPageChange(page: number, size: number) {
  currentPage.value = page
  pageSize.value = size
  search()
}
</script>
