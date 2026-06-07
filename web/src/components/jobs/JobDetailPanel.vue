<template>
  <div class="detail-panel" v-loading="loading">
    <div v-if="!job" class="detail-empty">
      <el-empty description="請選擇一個崗位查看詳情" />
    </div>
    <template v-else>
      <!-- 头部 -->
      <div class="detail-header">
        <div class="detail-header__top">
          <h2 class="detail-title">{{ job.title }}</h2>
          <el-button
            v-if="job.url"
            type="primary"
            link
            size="small"
            @click="openUrl(job.url)"
          >
            <el-icon><Link /></el-icon>
            查看原文
          </el-button>
        </div>
        <div class="detail-meta">
          <span>{{ job.company }}</span>
          <span class="detail-dot">·</span>
          <span>{{ job.location }}</span>
          <span class="detail-dot">·</span>
          <span>{{ job.source }}</span>
          <span v-if="job.import_time" class="detail-dot">·</span>
          <span v-if="job.import_time">{{ job.import_time }}</span>
        </div>
      </div>

      <!-- 薪资 -->
      <div v-if="job.salary_min || job.salary_max" class="detail-salary">
        <span class="detail-salary__label">薪資範圍</span>
        <span class="detail-salary__value">{{ formatSalary(job.salary_min, job.salary_max) }}</span>
        <span v-if="job.salary_currency" class="detail-salary__currency">{{ job.salary_currency }} / 月</span>
      </div>

      <!-- 技术栈 -->
      <div v-if="groupedSkills.length" class="detail-section">
        <h4 class="detail-section__title">技術棧</h4>
        <div v-for="group in groupedSkills" :key="group.category" class="detail-skill-group">
          <span class="detail-skill-group__label">{{ group.label }}</span>
          <div class="detail-skill-group__tags">
            <el-tag
              v-for="sk in group.skills"
              :key="sk"
              size="small"
              :type="skillTagType(group.category)"
              effect="plain"
            >
              {{ sk }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- JD 正文 -->
      <div class="detail-section">
        <h4 class="detail-section__title">職位描述</h4>
        <div class="detail-jd">
          <div v-if="job.jd_raw" v-html="job.jd_raw" class="detail-jd__html" />
          <div v-else-if="job.jd_text" class="detail-jd__text">{{ job.jd_text }}</div>
          <div v-else class="detail-jd__empty">暫無職位描述</div>
        </div>
      </div>

      <!-- 元信息 -->
      <div class="detail-section">
        <h4 class="detail-section__title">基本信息</h4>
        <div class="detail-info-grid">
          <div class="detail-info-item">
            <span class="detail-info-item__label">崗位 ID</span>
            <span class="detail-info-item__value">{{ job.job_id }}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-item__label">數據來源</span>
            <span class="detail-info-item__value">{{ job.source }}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-item__label">公司</span>
            <span class="detail-info-item__value">{{ job.company }}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-item__label">地區</span>
            <span class="detail-info-item__value">{{ job.location }}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-item__label">薪資範圍</span>
            <span class="detail-info-item__value">{{ formatSalary(job.salary_min, job.salary_max) }}</span>
          </div>
          <div v-if="job.employment_type" class="detail-info-item">
            <span class="detail-info-item__label">僱傭類型</span>
            <span class="detail-info-item__value">{{ job.employment_type }}</span>
          </div>
          <div v-if="job.posted_at" class="detail-info-item">
            <span class="detail-info-item__label">發布時間</span>
            <span class="detail-info-item__value">{{ job.posted_at }}</span>
          </div>
          <div v-if="job.industry_category" class="detail-info-item detail-info-item--full">
            <span class="detail-info-item__label">行業分類</span>
            <span class="detail-info-item__value">{{ job.industry_category }}</span>
          </div>
          <div v-if="job.application_volume" class="detail-info-item">
            <span class="detail-info-item__label">投遞熱度</span>
            <span class="detail-info-item__value">{{ job.application_volume }}</span>
          </div>
          <div v-if="job.import_time" class="detail-info-item">
            <span class="detail-info-item__label">導入時間</span>
            <span class="detail-info-item__value">{{ job.import_time }}</span>
          </div>
          <div v-if="job.url" class="detail-info-item detail-info-item--url">
            <span class="detail-info-item__label">原始鏈接</span>
            <a class="detail-info-item__value detail-info-item__link" :href="job.url" target="_blank" rel="noopener noreferrer">{{ job.url }}</a>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import type { JobItem } from '@/types'

const props = defineProps<{
  job: JobItem | null
  loading?: boolean
}>()

const categoryLabels: Record<string, string> = {
  programming_languages: '程式語言',
  frameworks_libraries: '框架與庫',
  cloud_devops: '雲服務與運維',
  databases: '數據庫與中間件',
  soft_skills: '軟技能',
}

const categoryColors: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
  programming_languages: '',
  frameworks_libraries: 'success',
  cloud_devops: 'warning',
  databases: 'danger',
  soft_skills: 'info',
}

const groupedSkills = computed(() => {
  const skills = props.job?.skills
  if (!skills) return []
  return Object.entries(skills)
    .filter(([, v]) => Array.isArray(v) && v.length > 0)
    .map(([cat, names]) => ({
      category: cat,
      label: categoryLabels[cat] || cat,
      skills: names as string[],
    }))
})

function skillTagType(cat: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return categoryColors[cat] || 'info'
}

function formatSalary(min?: number, max?: number): string {
  if (!min && !max) return '面議'
  const fmt = (n: number) => '$' + Math.round(n).toLocaleString()
  if (min && max && min < max) return `${fmt(min)} – ${fmt(max)}`
  if (min) return fmt(min) + '+'
  return '≤ ' + fmt(max!)
}

function openUrl(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>

<style scoped>
.detail-panel {
  background: #fff;
  border-radius: 6px;
  padding: 20px 24px;
  min-height: 400px;
  height: 100%;
  overflow-y: auto;
}
.detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
.detail-header {
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}
.detail-header__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.detail-title {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  line-height: 1.4;
}
.detail-meta {
  font-size: 13px;
  color: #909399;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
}
.detail-dot {
  margin: 0 2px;
  color: #c0c4cc;
}
.detail-salary {
  margin-top: 16px;
  padding: 14px 16px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.detail-salary__label {
  font-size: 13px;
  color: #e6a23c;
  font-weight: 500;
}
.detail-salary__value {
  font-size: 20px;
  font-weight: 700;
  color: #e6a23c;
}
.detail-salary__currency {
  font-size: 13px;
  color: #909399;
}
.detail-section {
  margin-top: 20px;
}
.detail-section__title {
  margin: 0 0 10px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  padding-left: 10px;
  border-left: 3px solid #409eff;
}
.detail-skill-group {
  margin-bottom: 8px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.detail-skill-group__label {
  font-size: 12px;
  color: #909399;
  min-width: 80px;
  flex-shrink: 0;
  line-height: 22px;
}
.detail-skill-group__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.detail-jd {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 14px 16px;
}
.detail-jd__html {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
}
.detail-jd__html :deep(p) {
  margin: 0 0 8px 0;
}
.detail-jd__html :deep(ul),
.detail-jd__html :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}
.detail-jd__html :deep(li) {
  margin-bottom: 2px;
}
.detail-jd__text {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  white-space: pre-wrap;
}
.detail-jd__empty {
  font-size: 13px;
  color: #c0c4cc;
  text-align: center;
  padding: 20px 0;
}
.detail-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.detail-info-item {
  display: flex;
  gap: 8px;
  font-size: 13px;
}
.detail-info-item__label {
  color: #909399;
  flex-shrink: 0;
}
.detail-info-item__value {
  color: #303133;
}
.detail-info-item--url {
  grid-column: 1 / -1;
}
.detail-info-item--full {
  grid-column: 1 / -1;
}
.detail-info-item__link {
  color: #409eff;
  text-decoration: none;
  word-break: break-all;
  font-size: 12px;
}
.detail-info-item__link:hover {
  text-decoration: underline;
}
</style>
