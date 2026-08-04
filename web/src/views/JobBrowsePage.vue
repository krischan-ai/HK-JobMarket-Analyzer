<template>
  <div class="job-browse">
    <h2 style="margin-top: 0; margin-bottom: 12px">
      <el-icon><Document /></el-icon> 崗位瀏覽
    </h2>

    <!-- 筛选栏 -->
    <JobFilterBar />

    <!-- 左右分栏 -->
    <div class="job-browse__body">
      <!-- 左侧岗位列表 -->
      <div class="job-browse__left">
        <div class="job-list-header">
          <span>共 <strong>{{ store.total }}</strong> 個崗位</span>
          <span v-if="store.hasActiveFilters" class="job-list-header__filtered">
            （已篩選）
            <el-button type="primary" link size="small" @click="clearFilters">清除</el-button>
          </span>
        </div>

        <!-- 加载态 -->
        <div v-if="store.loading" class="job-list-loading">
          <div v-for="n in 6" :key="n" class="job-card-skeleton">
            <div class="skeleton-line skeleton-line--title" />
            <div class="skeleton-line skeleton-line--meta" />
            <div class="skeleton-line skeleton-line--tags" />
          </div>
        </div>

        <!-- 空状态 -->
        <el-empty
          v-else-if="!store.jobs.length"
          description="暫無匹配崗位"
          :image-size="100"
          style="padding: 40px 0"
        />

        <!-- 岗位卡片 -->
        <div v-else class="job-list-cards">
          <JobCard
            v-for="job in store.jobs"
            :key="job.job_id"
            :job="job"
            :is-selected="store.selectedJob?.job_id === job.job_id"
            @select="store.selectJob(job)"
          />
        </div>

        <!-- 分页 -->
        <div v-if="store.total > store.pageSize" class="job-list-pagination">
          <el-pagination
            small
            :current-page="store.currentPage"
            :page-size="store.pageSize"
            :total="store.total"
            :page-sizes="[10, 20, 50]"
            layout="prev, pager, next, sizes"
            @current-change="(p: number) => store.goToPage(p)"
            @size-change="(s: number) => store.goToPage(1, s)"
          />
        </div>
      </div>

      <!-- 右侧详情面板 -->
      <div class="job-browse__right">
        <JobDetailPanel
          :job="store.selectedJob"
          :loading="store.loading && !store.jobs.length"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { onMounted } from 'vue'
import { useJobBrowseStore } from '@/stores/jobBrowse'
import JobFilterBar from '@/components/jobs/JobFilterBar.vue'
import JobCard from '@/components/jobs/JobCard.vue'
import JobDetailPanel from '@/components/jobs/JobDetailPanel.vue'

const store = useJobBrowseStore()

function clearFilters() {
  store.resetFilters()
  store.search()
}

onMounted(() => {
  store.fetchJobs()
})
</script>

<style scoped>
.job-browse {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
}
.job-browse__body {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.job-browse__left {
  width: 33.333%;
  min-width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}
.job-browse__right {
  flex: 1;
  min-width: 0;
}
.job-list-header {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.job-list-header__filtered {
  color: #e6a23c;
}
.job-list-cards {
  padding-right: 4px;
}
.job-list-loading {
  padding-right: 4px;
}
.job-card-skeleton {
  padding: 12px 14px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 8px;
  background: #fff;
}
.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, #f2f2f2 25%, #e6e6e6 50%, #f2f2f2 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
}
.skeleton-line--title {
  width: 70%;
  height: 16px;
}
.skeleton-line--meta {
  width: 50%;
  margin-top: 8px;
}
.skeleton-line--tags {
  width: 60%;
  margin-top: 8px;
  height: 20px;
}
@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.job-list-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
}
.job-list-pagination :deep(.el-pagination) {
  justify-content: center;
  flex-wrap: wrap;
}
</style>
