<template>
  <el-card class="result-panel" shadow="never">
    <template #header>
      <div class="panel-header">
        <span>生成結果</span>
        <div class="actions">
          <el-button :disabled="!store.result?.markdown" :icon="CopyDocument" text @click="store.copyMarkdown" />
          <el-button :disabled="!store.result?.markdown" :icon="Download" text @click="store.downloadMarkdown" />
        </div>
      </div>
    </template>

    <el-empty v-if="!store.result && !store.loading" description="生成後會在這裡展示完整簡歷與證據鏈" />

    <!-- 流式进度横幅 -->
    <div v-if="store.loading && store.stageMessage" class="stream-banner">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span class="banner-text">{{ store.stageMessage }}</span>
      <el-tag v-if="store.currentStep" size="small" type="info">{{ store.currentStep }}</el-tag>
    </div>

    <!-- token 实时输出 -->
    <div v-if="store.loading && store.streamingText" class="stream-text">
      <pre>{{ store.streamingText }}</pre>
    </div>

    <div v-else-if="store.loading && !store.stageMessage" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <el-tabs v-if="store.result" v-model="store.activeTab" class="tabs">
      <el-tab-pane label="生成簡歷" name="resume">
        <pre class="markdown">{{ store.result?.markdown || '生成中…' }}</pre>
      </el-tab-pane>

      <el-tab-pane label="崗位畫像" name="profile">
        <section v-if="profile" class="stack">
          <div class="status-row">
            <el-tag :type="confidenceType(profile.confidence)">{{ formatConfidence(profile.confidence) }}</el-tag>
            <span>{{ profile.source_coverage_note }}</span>
          </div>
          <h3>{{ profile.target_role }}</h3>
          <BlockList title="核心能力" :items="profile.core_capabilities" />
          <BlockList title="高頻技能" :items="profile.high_frequency_skills.map((s) => `${s.skill} (${s.count})`)" />
          <div v-if="profile.tech_stack?.length" class="tech-stack">
            <h3>技術棧</h3>
            <div v-for="group in profile.tech_stack" :key="group.category" class="tech-group">
              <el-tag size="small" type="info">{{ group.category }}</el-tag>
              <span class="tech-items">{{ group.items?.join('、') }}</span>
            </div>
          </div>
          <BlockList title="常見職責" :items="profile.common_responsibilities" />
          <BlockList title="隱性門檻" :items="profile.hidden_requirements" />
        </section>
      </el-tab-pane>

      <el-tab-pane label="能力匹配" name="match">
        <div class="stack">
          <el-table :data="store.result?.capability_matches || []" size="small">
            <el-table-column prop="capability" label="能力" min-width="180" />
            <el-table-column label="證據" width="110">
              <template #default="scope">{{ formatEvidence(scope.row.evidence_strength) }}</template>
            </el-table-column>
            <el-table-column prop="matched_sources" label="來源" min-width="140">
              <template #default="scope">{{ scope.row.matched_sources?.join(', ') }}</template>
            </el-table-column>
            <el-table-column prop="resume_angle" label="表達角度" min-width="220" />
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="選材依據" name="selection">
        <section v-if="plan" class="stack">
          <el-alert :title="plan.selection_summary" type="info" :closable="false" />
          <h3>選用素材</h3>
          <el-table :data="plan.selected" size="small">
            <el-table-column prop="source_title" label="素材" min-width="180" />
            <el-table-column prop="source_type" label="來源類型" width="110">
              <template #default="scope">
                <el-tag :type="scope.row.source_type === 'knowledge_base' ? 'warning' : ''" size="small">
                  {{ formatSourceType(scope.row.source_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="target_capability" label="對應能力" min-width="180" />
            <el-table-column label="證據" width="100">
              <template #default="scope">{{ formatEvidence(scope.row.evidence_confidence) }}</template>
            </el-table-column>
            <el-table-column prop="selection_reason" label="原因" min-width="220" />
          </el-table>
          <BlockList title="需要確認" :items="plan.user_confirmation_required" />
          <h3>排除素材</h3>
          <el-table :data="plan.excluded" size="small">
            <el-table-column prop="source_title" label="素材" min-width="180" />
            <el-table-column prop="reason" label="原因" min-width="240" />
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="證據審計" name="audit">
        <el-table :data="store.result?.claim_audit || []" size="small">
          <el-table-column prop="claim" label="Claim" min-width="260" />
          <el-table-column label="置信" width="90">
            <template #default="scope">{{ formatEvidence(scope.row.confidence) }}</template>
          </el-table-column>
          <el-table-column label="來源" width="150">
            <template #default="scope">{{ formatSource(scope.row.source) }}</template>
          </el-table-column>
          <el-table-column label="建議" width="110">
            <template #default="scope">{{ formatAction(scope.row.action) }}</template>
          </el-table-column>
          <el-table-column prop="reason" label="原因" min-width="220" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="質量閘門" name="quality">
        <section v-if="quality" class="stack">
          <el-result :icon="qualityIcon" :title="formatQuality(quality.status)" />
          <BlockList title="P0 風險" :items="quality.p0_violations" />
          <BlockList title="P1 缺口" :items="quality.p1_gaps" />
          <BlockList title="建議修復" :items="quality.suggested_fixes" />
        </section>
        <el-alert v-if="store.result?.input_health" :title="formatInputHealth(store.result.input_health)" type="warning" :closable="false" />
      </el-tab-pane>

      <el-tab-pane label="相似崗位" name="jobs">
        <el-table :data="store.result?.similar_jobs || []" size="small">
          <el-table-column prop="title" label="職位" min-width="180" />
          <el-table-column prop="company" label="公司" min-width="160" />
          <el-table-column prop="location" label="地點" width="120" />
          <el-table-column prop="match_reason" label="匹配理由" min-width="240" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script lang="ts" setup>
import { computed, defineComponent, h } from 'vue'
import { CopyDocument, Download, Loading } from '@element-plus/icons-vue'
import { useResumeGenerateStore } from '@/stores/resumeGenerate'
import type { GenerateInputHealth } from '@/api/resumeGenerate'

const store = useResumeGenerateStore()
const profile = computed(() => store.result?.target_job_profile || null)
const plan = computed(() => store.result?.selected_experience_plan || null)
const quality = computed(() => store.result?.quality_gate || null)
const qualityIcon = computed(() => (quality.value?.status === 'blocked' ? 'error' : quality.value?.status === 'pass' ? 'success' : 'warning'))

function confidenceType(value: string) {
  if (value === 'high') return 'success'
  if (value === 'low') return 'warning'
  return 'info'
}

function formatConfidence(value: string) {
  const labels: Record<string, string> = {
    high: '高置信',
    medium: '中等置信',
    low: '低置信',
  }
  return labels[value] || value || '-'
}

function formatEvidence(value: string) {
  const labels: Record<string, string> = {
    strong: '强证据',
    medium: '中等证据',
    weak: '弱证据',
    risky: '高风险',
    missing: '缺少证据',
  }
  return labels[value] || value || '-'
}

function formatSource(value: string) {
  const labels: Record<string, string> = {
    resume: '原简历',
    selected_experience: '已选素材',
    knowledge_base: '知识库岗位',
    inferred: '模型推断',
    user_confirmed: '用户确认',
  }
  return labels[value] || value || '-'
}

function formatAction(value: string) {
  const labels: Record<string, string> = {
    keep: '保留',
    soften: '弱化',
    remove: '删除',
    ask_user: '询问确认',
  }
  return labels[value] || value || '-'
}

function formatQuality(value: string) {
  const labels: Record<string, string> = {
    pass: '通过',
    pass_with_gaps: '通过但有缺口',
    blocked: '阻断',
  }
  return labels[value] || value || '-'
}

function formatSourceType(value: string) {
  const labels: Record<string, string> = {
    work: '工作经历',
    project: '项目经历',
    education: '教育',
    skill: '技能',
    knowledge_base: '知识库',
  }
  return labels[value] || value || '-'
}

function formatInputHealth(health: GenerateInputHealth) {
  const parts: string[] = []
  if (health.gaps?.length) parts.push(...health.gaps)
  if (health.blocking_questions?.length) parts.push(...health.blocking_questions)
  return parts.join('；') || '输入体检通过'
}

const BlockList = defineComponent({
  props: {
    title: { type: String, required: true },
    items: { type: Array as () => string[], required: true },
  },
  setup(props) {
    return () => h('section', { class: 'block-list' }, [
      h('h3', props.title),
      props.items.length
        ? h('ul', props.items.map((item) => h('li', item)))
        : h('p', { class: 'muted' }, '暫無資料'),
    ])
  },
})
</script>

<style scoped>
.result-panel {
  min-width: 0;
}

.panel-header,
.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-header {
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 4px;
}

.loading-state {
  padding: 8px;
}

.stream-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: #ecf5ff;
  border-radius: 6px;
  font-size: 13px;
  color: #409eff;
}

.banner-text {
  flex: 1;
}

.stream-text {
  margin-bottom: 12px;
}

.stream-text pre {
  max-height: 200px;
  overflow: auto;
  margin: 0;
  padding: 10px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #fafafa;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  color: #606266;
}

.tabs {
  min-height: 520px;
}

.markdown {
  min-height: 520px;
  max-height: 70vh;
  overflow: auto;
  margin: 0;
  padding: 16px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #fafafa;
  color: #303133;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.stack {
  display: grid;
  gap: 14px;
}

h3 {
  margin: 0;
  font-size: 15px;
}

.tech-stack {
  display: grid;
  gap: 8px;
}

.tech-group {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.tech-items {
  font-size: 13px;
  line-height: 1.6;
}

.block-list ul {
  margin: 8px 0 0;
  padding-left: 20px;
}

.block-list li {
  margin: 5px 0;
  line-height: 1.5;
}

.muted {
  margin: 6px 0 0;
  color: #909399;
}
</style>
