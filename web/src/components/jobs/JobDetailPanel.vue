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

      <!-- 保险销售警告 -->
      <div v-if="job.is_insurance_sales" class="detail-alert detail-alert--warning">
        <el-icon><WarningFilled /></el-icon>
        <div class="detail-alert__body">
          <div class="detail-alert__title">保險銷售崗位標記</div>
          <div class="detail-alert__desc">
            系統判定該崗位疑似保險銷售（保險得分 {{ job.insurance_score ?? 0 }}）
          </div>
          <div v-if="insuranceReasons.length" class="detail-alert__reasons">
            <span v-for="(r, i) in insuranceReasons" :key="i" class="detail-alert__reason">{{ r }}</span>
          </div>
        </div>
      </div>

      <!-- 薪资 -->
      <div v-if="job.salary_min || job.salary_max" class="detail-salary">
        <span class="detail-salary__label">薪資範圍</span>
        <span class="detail-salary__value">{{ formatSalary(job.salary_min, job.salary_max) }}</span>
        <span v-if="job.salary_currency" class="detail-salary__currency">{{ job.salary_currency }} / 月</span>
      </div>

      <!-- 岗位标签 -->
      <div v-if="jobTags.length" class="detail-section">
        <h4 class="detail-section__title">崗位標籤</h4>
        <div class="detail-tags">
          <el-tag
            v-for="tag in jobTags"
            :key="tag.label"
            :type="tag.type"
            effect="light"
            round
          >
            {{ tag.label }}
          </el-tag>
        </div>
      </div>

      <!-- 技术栈（平铺） -->
      <div v-if="techStackList.length" class="detail-section">
        <h4 class="detail-section__title">技術棧</h4>
        <div class="detail-tech-stack">
          <el-tag
            v-for="tech in techStackList"
            :key="tech"
            size="small"
            effect="plain"
          >
            {{ tech }}
          </el-tag>
        </div>
      </div>

      <!-- 技能分类（skills 分组） -->
      <div v-if="groupedSkills.length" class="detail-section">
        <h4 class="detail-section__title">技能分類</h4>
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

      <!-- 非技术能力要求 -->
      <div v-if="softSkillGroups.length" class="detail-section">
        <h4 class="detail-section__title">非技術能力要求</h4>
        <div v-for="group in softSkillGroups" :key="group.category" class="detail-skill-group">
          <span class="detail-skill-group__label">{{ group.label }}</span>
          <div class="detail-skill-group__tags">
            <el-tag
              v-for="sk in group.skills"
              :key="group.category + sk"
              size="small"
              :type="softSkillTagType(group.category)"
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
          <pre v-if="jdDisplay" class="detail-jd__text">{{ jdDisplay }}</pre>
          <div v-else class="detail-jd__empty">暫無職位描述</div>
        </div>
      </div>

      <!-- 雇主问题 / 面试问题 -->
      <div v-if="employerQuestions.length" class="detail-section">
        <h4 class="detail-section__title">僱主問題 / 面試問題</h4>
        <ol class="detail-questions">
          <li v-for="(q, i) in employerQuestions" :key="i">{{ q }}</li>
        </ol>
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
          <div v-if="job.work_mode" class="detail-info-item">
            <span class="detail-info-item__label">工作模式</span>
            <span class="detail-info-item__value">{{ workModeLabel(job.work_mode) }}</span>
          </div>
          <div v-if="job.job_type" class="detail-info-item">
            <span class="detail-info-item__label">崗位類型</span>
            <span class="detail-info-item__value">{{ jobTypeLabel(job.job_type) }}</span>
          </div>
          <div v-if="job.education_required" class="detail-info-item">
            <span class="detail-info-item__label">學歷要求</span>
            <span class="detail-info-item__value">{{ educationLabel(job.education_required) }}</span>
          </div>
          <div v-if="languagesLabel" class="detail-info-item detail-info-item--full">
            <span class="detail-info-item__label">語言要求</span>
            <span class="detail-info-item__value">{{ languagesLabel }}</span>
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
          <div v-if="job.company_size" class="detail-info-item">
            <span class="detail-info-item__label">公司規模</span>
            <span class="detail-info-item__value">{{ job.company_size }}</span>
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

const workModeMap: Record<string, string> = {
  hybrid: '混合辦公',
  remote: '遠端工作',
  on_site: '全職坐班',
  onsite: '全職坐班',
  office: '全職坐班',
}

const jobTypeMap: Record<string, string> = {
  full_time: '全職',
  'full-time': '全職',
  part_time: '兼職',
  'part-time': '兼職',
  internship: '實習',
  contract: '合約',
  temporary: '臨時',
  freelance: '自由職業',
}

const educationMap: Record<string, string> = {
  bachelor: '學士',
  master: '碩士',
  phd: '博士',
  doctorate: '博士',
  diploma: '文憑',
  associate: '副學士',
  'high school': '中學',
  secondary: '中學',
  none: '不限',
  '': '不限',
}

const languageMap: Record<string, string> = {
  mandarin: '普通話',
  cantonese: '廣東話',
  english: '英語',
  japanese: '日語',
  korean: '韓語',
  french: '法語',
  german: '德語',
  spanish: '西班牙語',
  putonghua: '普通話',
}

function workModeLabel(v: string): string {
  return workModeMap[v?.toLowerCase().trim()] || v
}

function jobTypeLabel(v: string): string {
  return jobTypeMap[v?.toLowerCase().trim()] || v
}

function educationLabel(v: string): string {
  return educationMap[v?.toLowerCase().trim()] || v
}

function languageLabel(v: string): string {
  return languageMap[v?.toLowerCase().trim()] || v
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

const softSkillGroups = computed(() => {
  const softSkills = props.job?.soft_skills
  if (!softSkills) return []
  return [
    { category: 'education', label: '學歷要求', skills: softSkills.education ?? [] },
    { category: 'language', label: '語言要求', skills: softSkills.language ?? [] },
    { category: 'soft_skill', label: '個人能力', skills: softSkills.soft_skill ?? [] },
    { category: 'domain_knowledge', label: '行業知識', skills: softSkills.domain_knowledge ?? [] },
    { category: 'certification', label: '資格證', skills: softSkills.certification ?? [] },
    { category: 'business_skill', label: '業務交付', skills: softSkills.business_skill ?? [] },
  ].filter((group) => group.skills.length > 0)
})

const techStackList = computed(() => {
  return props.job?.tech_stack ?? []
})

const employerQuestions = computed(() => {
  return props.job?.employer_questions ?? []
})

const insuranceReasons = computed(() => {
  return props.job?.insurance_reasons ?? []
})

const languagesLabel = computed(() => {
  const langs = props.job?.languages_required
  if (!langs || !langs.length) return ''
  return langs.map(languageLabel).join('、')
})

// JD 展示文本：优先 jd_raw（保留原始换行），回退 jd_text
// 压缩连续空白（含不间断空格 \xa0）为单个空格，但保留换行符
const jdDisplay = computed(() => {
  const raw = props.job?.jd_raw?.trim()
  const text = raw || props.job?.jd_text?.trim() || ''
  if (!text) return ''
  return text.replace(/[^\S\n]+/g, ' ')
})

// 岗位标签
const jobTags = computed<{ label: string; type: '' | 'success' | 'warning' | 'danger' | 'info' }[]>(() => {
  const tags: { label: string; type: '' | 'success' | 'warning' | 'danger' | 'info' }[] = []
  if (props.job?.industry_category) {
    tags.push({ label: '行业：' + props.job.industry_category, type: 'info' })
  }
  if (props.job?.work_mode) {
    tags.push({ label: '工作模式：' + workModeLabel(props.job.work_mode), type: 'success' })
  }
  if (props.job?.job_type) {
    tags.push({ label: '崗位類型：' + jobTypeLabel(props.job.job_type), type: '' })
  }
  if (props.job?.employment_type) {
    tags.push({ label: '僱傭：' + props.job.employment_type, type: 'info' })
  }
  if (props.job?.education_required) {
    tags.push({ label: '學歷：' + educationLabel(props.job.education_required), type: 'warning' })
  }
  if (props.job?.languages_required?.length) {
    tags.push({ label: '語言：' + props.job.languages_required.map(languageLabel).join('、'), type: 'danger' })
  }
  return tags
})

function skillTagType(cat: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return categoryColors[cat] || 'info'
}

function softSkillTagType(cat: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  if (cat === 'education') return 'danger'
  if (cat === 'language') return 'warning'
  if (cat === 'domain_knowledge') return 'success'
  if (cat === 'certification') return 'danger'
  return 'info'
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
.detail-alert {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 6px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.detail-alert--warning {
  background: #fdf6ec;
  border: 1px solid #f5dab1;
  color: #e6a23c;
}
.detail-alert__body {
  flex: 1;
  min-width: 0;
}
.detail-alert__title {
  font-size: 14px;
  font-weight: 600;
  color: #b88230;
}
.detail-alert__desc {
  font-size: 12px;
  color: #937031;
  margin-top: 2px;
}
.detail-alert__reasons {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.detail-alert__reason {
  font-size: 11px;
  background: #fff;
  border: 1px solid #f5dab1;
  border-radius: 4px;
  padding: 1px 6px;
  color: #937031;
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
.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.detail-tech-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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
.detail-jd__text {
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  color: #606266;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  text-align: justify;
}
.detail-jd__empty {
  font-size: 13px;
  color: #c0c4cc;
  text-align: center;
  padding: 20px 0;
}
.detail-questions {
  margin: 0;
  padding-left: 22px;
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}
.detail-questions li {
  margin-bottom: 6px;
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
