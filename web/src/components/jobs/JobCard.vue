<template>
  <div
    class="job-card"
    :class="{ 'job-card--selected': isSelected }"
    @click="$emit('select')"
  >
    <div class="job-card__header">
      <h3 class="job-card__title">{{ job.title }}</h3>
      <span v-if="job.salary_min || job.salary_max" class="job-card__salary">
        {{ formatSalary(job.salary_min, job.salary_max) }}
      </span>
    </div>
    <div class="job-card__meta">
      <span class="job-card__company">{{ job.company }}</span>
      <span class="job-card__dot">·</span>
      <span class="job-card__location">{{ job.location }}</span>
      <span v-if="job.employment_type" class="job-card__dot">·</span>
      <span v-if="job.employment_type" class="job-card__employment-type">{{ job.employment_type }}</span>
    </div>
    <div v-if="skillList.length" class="job-card__skills">
      <el-tag
        v-for="(sk, i) in skillList.slice(0, 4)"
        :key="i"
        size="small"
        :type="skillTagType(sk.category)"
        effect="plain"
      >
        {{ sk.name }}
      </el-tag>
      <span v-if="skillList.length > 4" class="job-card__skill-more">+{{ skillList.length - 4 }}</span>
    </div>
    <div v-if="softSkillList.length" class="job-card__skills job-card__skills--soft">
      <el-tag
        v-for="tag in softSkillList.slice(0, 4)"
        :key="tag.category + tag.name"
        size="small"
        :type="softSkillTagType(tag.category)"
        effect="plain"
      >
        {{ tag.name }}
      </el-tag>
      <span v-if="softSkillList.length > 4" class="job-card__skill-more">+{{ softSkillList.length - 4 }}</span>
    </div>
    <div class="job-card__footer">
      <span class="job-card__source">{{ job.source }}</span>
      <span class="job-card__footer-right">
        <span v-if="job.posted_at" class="job-card__time">{{ job.posted_at }}</span>
        <span v-if="job.industry_category" class="job-card__time">· {{ job.industry_category }}</span>
      </span>
      <a
        v-if="job.url"
        :href="job.url"
        target="_blank"
        rel="noopener noreferrer"
        class="job-card__url"
        title="查看原文"
        @click.stop
      >
        <el-icon><Link /></el-icon>
      </a>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import type { JobItem } from '@/types'

const props = defineProps<{
  job: JobItem
  isSelected: boolean
}>()

defineEmits<{ (e: 'select'): void }>()

const skillTagColors: Record<string, string> = {
  programming_languages: '',
  frameworks_libraries: 'success',
  cloud_devops: 'warning',
  databases: 'danger',
  soft_skills: 'info',
}

const skillList = computed(() => {
  const skills = props.job.skills
  if (!skills) return []
  const list: Array<{ name: string; category: string }> = []
  for (const [cat, names] of Object.entries(skills)) {
    if (Array.isArray(names)) {
      for (const n of names) list.push({ name: n, category: cat })
    }
  }
  return list
})

const softSkillList = computed(() => {
  const softSkills = props.job.soft_skills
  if (!softSkills) return []
  return [
    ...softSkills.education.map((name) => ({ name, category: 'education' })),
    ...softSkills.language.map((name) => ({ name, category: 'language' })),
    ...softSkills.soft_skill.map((name) => ({ name, category: 'soft_skill' })),
  ].filter((item) => item.name)
})

function skillTagType(cat: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return (skillTagColors[cat] || 'info') as '' | 'success' | 'warning' | 'danger' | 'info'
}

function softSkillTagType(cat: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  if (cat === 'education') return 'danger'
  if (cat === 'language') return 'warning'
  return 'info'
}

function formatSalary(min?: number, max?: number): string {
  if (!min && !max) return '面議'
  const fmt = (n: number) => '$' + Math.round(n).toLocaleString()
  if (min && max && min < max) return `${fmt(min)} – ${fmt(max)}`
  if (min) return fmt(min) + '+'
  return '≤ ' + fmt(max!)
}
</script>

<style scoped>
.job-card {
  padding: 12px 14px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.15s;
  background: #fff;
}
.job-card:hover {
  border-color: #409eff;
  box-shadow: 0 1px 4px rgba(64,158,255,.15);
}
.job-card--selected {
  border-color: #409eff;
  background: #ecf5ff;
}
.job-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.job-card__title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.job-card__salary {
  font-size: 13px;
  color: #e6a23c;
  white-space: nowrap;
  flex-shrink: 0;
}
.job-card__meta {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}
.job-card__dot {
  color: #c0c4cc;
}
.job-card__skills {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}
.job-card__skills--soft {
  margin-top: 5px;
}
.job-card__skill-more {
  font-size: 11px;
  color: #909399;
}
.job-card__footer {
  margin-top: 6px;
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #c0c4cc;
  align-items: center;
}
.job-card__url {
  color: #c0c4cc;
  text-decoration: none;
  display: flex;
  align-items: center;
  font-size: 14px;
}
.job-card__url:hover {
  color: #409eff;
}
</style>
