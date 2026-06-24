<template>
  <el-card shadow="never" class="result-card">
    <template #header>
      <div class="card-header">
        <span>潤色結果</span>
        <div class="header-actions">
          <el-button size="small" :disabled="!store.result" @click="copySuggestions">複製建議</el-button>
          <el-button size="small" :disabled="!store.result" @click="downloadMarkdown">導出 Markdown</el-button>
        </div>
      </div>
    </template>

    <el-empty
      v-if="!store.result && !store.loading && !store.streaming"
      description="提交簡歷後，這裡會流式顯示分析結果"
    />
    <div v-else-if="!store.result && store.loading" class="loading-box">
      <el-skeleton :rows="10" animated />
    </div>

    <template v-else>
      <div v-if="store.streaming" class="stage-banner">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ store.stageMessage || '分析中…' }}</span>
      </div>

      <el-tabs v-model="store.activeTab">
      <el-tab-pane label="整體評分" name="score">
        <div v-if="score" class="score-layout">
          <div class="overall-score">
            <div class="score-number">{{ score.overall_score.toFixed(1) }}</div>
            <div class="score-label">綜合分</div>
          </div>
          <div class="score-bars">
            <div v-for="item in scoreItems" :key="item.label" class="score-row">
              <div class="score-row-head">
                <span>{{ item.label }}</span>
                <el-progress :percentage="item.value * 10" :format="() => item.value.toFixed(1)" />
              </div>
              <div v-if="item.reason" class="score-reason">{{ item.reason }}</div>
            </div>
          </div>
        </div>

        <el-alert
          v-if="score?.overall_comment"
          type="success"
          :closable="false"
          show-icon
          class="suggestion-alert"
          title="评分说明"
        >
          <template #default>{{ score.overall_comment }}</template>
        </el-alert>

        <el-alert
          v-for="suggestion in score?.suggestions || []"
          :key="suggestion"
          :title="suggestion"
          type="info"
          :closable="false"
          class="suggestion-alert"
        />
      </el-tab-pane>

      <el-tab-pane label="逐段對比" name="diff">
        <div v-if="sections.length" class="section-list">
          <el-card v-for="(section, index) in sections" :key="`${section.section}-${index}`" shadow="never" class="section-card">
            <template #header>
              <div class="section-title">
                <span>{{ section.section }}</span>
                <el-tag v-for="keyword in section.keywords_added" :key="keyword" size="small">{{ keyword }}</el-tag>
              </div>
            </template>
            <div class="diff-grid">
              <div>
                <div class="diff-label">原文</div>
                <pre>{{ section.original || '未提供原文片段' }}</pre>
              </div>
              <div>
                <div class="diff-label">潤色後</div>
                <pre>{{ section.suggested }}</pre>
              </div>
            </div>
            <el-divider />
            <el-tag v-for="change in section.changes" :key="change" type="success" effect="plain" class="change-tag">
              {{ change }}
            </el-tag>
          </el-card>
        </div>
        <el-empty v-else description="暫無逐段建議" />
      </el-tab-pane>

      <el-tab-pane label="差距分析" name="gap">
        <div class="gap-grid">
          <el-card shadow="never">
            <template #header>技能匹配</template>
            <div class="tag-section">
              <div class="tag-label">已匹配</div>
              <el-tag v-for="skill in gapList('matched_skills')" :key="skill" type="success">{{ skill }}</el-tag>
            </div>
            <div class="tag-section">
              <div class="tag-label">缺失</div>
              <el-tag v-for="skill in gapList('missing_skills')" :key="skill" type="danger">{{ skill }}</el-tag>
            </div>
            <div class="tag-section">
              <div class="tag-label">需加強</div>
              <el-tag v-for="skill in gapList('weak_skills')" :key="skill" type="warning">{{ skill }}</el-tag>
            </div>
          </el-card>

          <el-card shadow="never">
            <template #header>關鍵詞建議</template>
            <el-table :data="keywordSuggestions" size="small" empty-text="暫無建議">
              <el-table-column prop="keyword" label="關鍵詞" min-width="120" />
              <el-table-column prop="priority" label="優先級" width="90" />
              <el-table-column prop="placement" label="位置" width="110" />
            </el-table>
          </el-card>
        </div>

        <el-alert
          v-if="store.result?.gap_analysis?.experience_gap"
          :title="store.result.gap_analysis.experience_gap"
          type="warning"
          :closable="false"
          class="suggestion-alert"
        />

        <el-alert
          v-if="marketDemandAnalysis"
          type="success"
          :closable="false"
          show-icon
          class="suggestion-alert"
          title="市場需求分析（基於知識庫岗位數據）"
        >
          <template #default>{{ marketDemandAnalysis }}</template>
        </el-alert>

        <div v-if="roleDemandRanking.length || techStackRanking.length" class="gap-grid">
          <el-card v-if="roleDemandRanking.length" shadow="never">
            <template #header>需求量最大的岗位方向 Top {{ roleDemandRanking.length }}</template>
            <el-table :data="roleDemandRanking" size="small">
              <el-table-column type="index" label="#" width="48" />
              <el-table-column prop="role_name" label="岗位方向" min-width="140" />
              <el-table-column prop="count" label="岗位数" width="80" align="right" />
            </el-table>
          </el-card>

          <el-card v-if="techStackRanking.length" shadow="never">
            <template #header>JD 技術棧提及次數 Top {{ techStackRanking.length }}</template>
            <el-table :data="techStackRanking" size="small">
              <el-table-column type="index" label="#" width="48" />
              <el-table-column prop="skill" label="技術棧" min-width="140" />
              <el-table-column prop="count" label="次數" width="80" align="right" />
            </el-table>
          </el-card>
        </div>

        <el-card v-if="marketSkills.length" shadow="never" class="jobs-card">
          <template #header>香港市場高頻技能（來自知識庫相似崗位）</template>
          <el-tag
            v-for="item in marketSkills"
            :key="item.skill"
            type="info"
            effect="plain"
            class="market-tag"
          >
            {{ item.skill }} · {{ item.count }}
          </el-tag>
        </el-card>

        <el-card shadow="never" class="jobs-card">
          <template #header>相似香港崗位</template>
          <el-table :data="store.result?.matched_jobs || []" size="small" empty-text="暫無相似崗位">
            <el-table-column prop="title" label="職位" min-width="180" />
            <el-table-column prop="company" label="公司" min-width="140" />
            <el-table-column prop="location" label="地點" width="120" />
            <el-table-column prop="score" label="相似度" width="90" />
          </el-table>
        </el-card>
      </el-tab-pane>
      </el-tabs>
    </template>
  </el-card>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useResumeStore } from '@/stores/resume'

const store = useResumeStore()

const score = computed(() => store.result?.score || null)
const sections = computed(() => store.result?.polish_suggestions || [])
const keywordSuggestions = computed(() => store.result?.gap_analysis?.keyword_suggestions || [])
const marketSkills = computed(() => store.result?.market_context?.top_skills || [])
const marketDemandAnalysis = computed(() => store.result?.gap_analysis?.market_demand_analysis || '')
const roleDemandRanking = computed(() => store.result?.market_insights?.role_demand_ranking || [])
const techStackRanking = computed(() => store.result?.market_insights?.tech_stack_ranking || [])
const scoreItems = computed(() => {
  if (!score.value) return []
  const reasons = score.value.dimension_reasons || {}
  return [
    { label: '關鍵詞覆蓋', value: score.value.keyword_coverage, reason: reasons.keyword_coverage },
    { label: '經驗匹配', value: score.value.experience_alignment, reason: reasons.experience_alignment },
    { label: '技能相關', value: score.value.skill_relevance, reason: reasons.skill_relevance },
    { label: '語言質量', value: score.value.language_quality, reason: reasons.language_quality },
  ]
})

function gapList(key: string) {
  const value = store.result?.gap_analysis?.[key]
  return Array.isArray(value) ? value : []
}

function buildMarkdown() {
  const lines: string[] = ['# 簡歷潤色建議', '']
  if (score.value) {
    lines.push(`綜合分：${score.value.overall_score.toFixed(1)}/10`, '')
  }
  for (const section of sections.value) {
    lines.push(`## ${section.section}`, '', '### 原文', section.original || '-', '', '### 潤色後', section.suggested || '-', '')
    if (section.changes.length) {
      lines.push('### 修改說明')
      section.changes.forEach((change) => lines.push(`- ${change}`))
      lines.push('')
    }
  }
  return lines.join('\n')
}

async function copySuggestions() {
  await navigator.clipboard.writeText(buildMarkdown())
  ElMessage.success('已複製潤色建議')
}

function downloadMarkdown() {
  const blob = new Blob([buildMarkdown()], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'resume-polish.md'
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.result-card {
  height: 100%;
}

.card-header,
.header-actions,
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-header {
  justify-content: space-between;
}

.loading-box {
  padding: 16px 0;
}

.stage-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
  border-radius: 6px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 13px;
}

.score-layout {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 24px;
  align-items: center;
}

.overall-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 150px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.score-number {
  font-size: 42px;
  font-weight: 700;
  color: #409eff;
  line-height: 1;
}

.score-label,
.diff-label,
.tag-label {
  color: #606266;
  font-size: 13px;
}

.score-row {
  margin-bottom: 14px;
}

.score-row-head {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 12px;
  align-items: center;
}

.score-reason {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin: 4px 0 0 102px;
}

.suggestion-alert {
  margin-top: 12px;
}

.section-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  flex-wrap: wrap;
}

.diff-grid,
.gap-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

pre {
  margin: 8px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.6;
  background: #f7f8fa;
  border-radius: 6px;
  padding: 12px;
}

.change-tag {
  margin: 0 6px 6px 0;
  white-space: normal;
  height: auto;
  line-height: 1.5;
  padding: 4px 8px;
}

.tag-section {
  margin-bottom: 14px;
}

.tag-section .el-tag {
  margin: 4px 6px 0 0;
}

.jobs-card {
  margin-top: 12px;
}

.market-tag {
  margin: 0 6px 6px 0;
}

@media (max-width: 900px) {
  .score-layout,
  .diff-grid,
  .gap-grid {
    grid-template-columns: 1fr;
  }
}
</style>
