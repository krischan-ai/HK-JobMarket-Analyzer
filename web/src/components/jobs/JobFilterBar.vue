<template>
  <div class="filter-bar">
    <el-input
      v-model="localKeyword"
      placeholder="搜尋崗位名稱、公司或 JD 內容..."
      clearable
      prefix-icon="Search"
      class="filter-search"
      @keyup.enter="handleSearch"
      @clear="handleSearch"
    />
    <el-select
      v-model="localSource"
      placeholder="數據來源"
      clearable
      class="filter-select"
      @change="handleSearch"
    >
      <el-option v-for="s in sources" :key="s" :label="s" :value="s" />
    </el-select>
    <el-select
      v-model="localLocation"
      placeholder="地區"
      clearable
      filterable
      class="filter-select"
      @change="handleSearch"
    >
      <el-option
        v-for="loc in locations"
        :key="loc.name"
        :label="`${loc.name} (${loc.count})`"
        :value="loc.name"
      />
    </el-select>
    <el-input-number
      v-model="localSalaryMin"
      placeholder="最低薪資"
      :min="0"
      :step="5000"
      :controls="false"
      class="filter-salary"
    />
    <span class="salary-sep">–</span>
    <el-input-number
      v-model="localSalaryMax"
      placeholder="最高薪資"
      :min="0"
      :step="5000"
      :controls="false"
      class="filter-salary"
    />
    <el-button type="primary" @click="handleSearch">
      <el-icon><Search /></el-icon>
      搜尋
    </el-button>
    <el-button v-if="hasActiveFilters" @click="handleReset">清除篩選</el-button>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useJobBrowseStore } from '@/stores/jobBrowse'

const store = useJobBrowseStore()
const { sources, locations, hasActiveFilters } = storeToRefs(store)

const localKeyword = ref(store.filters.keyword)
const localSource = ref(store.filters.source)
const localLocation = ref(store.filters.location)
const localSalaryMin = ref(store.filters.salaryMin)
const localSalaryMax = ref(store.filters.salaryMax)

watch(() => store.filters, (f) => {
  localKeyword.value = f.keyword
  localSource.value = f.source
  localLocation.value = f.location
  localSalaryMin.value = f.salaryMin
  localSalaryMax.value = f.salaryMax
}, { deep: true })

function handleSearch() {
  store.setFilter('keyword', localKeyword.value)
  store.setFilter('source', localSource.value || '')
  store.setFilter('location', localLocation.value || '')
  store.setFilter('salaryMin', localSalaryMin.value)
  store.setFilter('salaryMax', localSalaryMax.value)
  store.search()
}

function handleReset() {
  localKeyword.value = ''
  localSource.value = ''
  localLocation.value = ''
  localSalaryMin.value = null
  localSalaryMax.value = null
  store.resetFilters()
  store.search()
}

onMounted(() => {
  store.fetchSources()
  store.fetchLocations()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 16px;
  background: #fff;
  border-radius: 6px;
  margin-bottom: 12px;
}
.filter-search {
  flex: 1 1 260px;
  min-width: 200px;
}
.filter-select {
  width: 150px;
}
.filter-salary {
  width: 130px;
}
.salary-sep {
  color: #909399;
  flex-shrink: 0;
}
</style>
