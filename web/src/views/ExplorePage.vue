<template>
  <div>
    <h2 style="margin-top: 0">數據探索</h2>
    <el-card>
      <el-form :inline="true" style="margin-bottom: 16px">
        <el-form-item>
          <el-input v-model="searchText" placeholder="搜索岗位/技能/公司..." clearable style="width: 350px" @keyup.enter="doSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="doSearch">搜索</el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="exportCSV" :disabled="!results.length">
            <el-icon><Download /></el-icon> 導出 CSV
          </el-button>
        </el-form-item>
      </el-form>

      <DataTable :data="results" :loading="searching" max-height="500" empty-text="輸入關鍵詞開始搜索">
        <el-table-column prop="job_id" label="Job ID" width="150" />
        <el-table-column prop="title" label="崗位名稱" min-width="200">
          <template #default="{ row }"><el-link type="primary">{{ row.title }}</el-link></template>
        </el-table-column>
        <el-table-column prop="company" label="公司" width="150" />
        <el-table-column prop="location" label="地點" width="110" />
      </DataTable>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import api from '@/api'
import DataTable from '@/components/common/DataTable.vue'

const searchText = ref('')
const results = ref<{ job_id: string; title: string; company: string; location: string }[]>([])
const searching = ref(false)

async function doSearch() {
  if (!searchText.value.trim()) return
  searching.value = true
  try {
    const { data } = await api.get('/knowledge/search', { params: { kw: searchText.value } })
    results.value = data
  } finally {
    searching.value = false
  }
}

function exportCSV() {
  const header = 'job_id,title,company,location\n'
  const rows = results.value.map(r => `${r.job_id},${r.title},${r.company},${r.location}`).join('\n')
  const blob = new Blob([header + rows], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'search_results.csv'; a.click()
  URL.revokeObjectURL(url)
}
</script>
