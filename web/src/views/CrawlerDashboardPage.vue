<template>
  <div>
    <h2 style="margin-top: 0">爬蟲控制台</h2>

    <!-- 爬蟲控制區 -->
    <el-card style="margin-bottom: 16px">
      <template #header><span><el-icon><VideoPlay /></el-icon> 新建爬取任務</span></template>
      <el-form :inline="true">
        <el-form-item label="關鍵詞">
          <el-select-v2
            v-model="form.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="輸入關鍵詞後按 Enter 添加"
            style="width: 380px"
            :options="[]"
          />
        </el-form-item>
        <el-form-item label="數據源">
          <el-checkbox-group v-model="form.sources">
            <el-checkbox
              v-for="s in availableSourceOptions"
              :key="s.value"
              :label="s.value"
              :value="s.value"
            >{{ s.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="後處理">
          <el-checkbox v-model="form.post_cleaning">清洗</el-checkbox>
          <el-checkbox v-model="form.post_extraction">提取</el-checkbox>
          <el-checkbox v-model="form.post_classification">分類</el-checkbox>
          <el-checkbox v-model="form.post_kb_import">知識庫</el-checkbox>
          <el-checkbox v-model="form.post_vector_index">向量索引</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="creating" @click="handleCreate">
            <el-icon><VideoPlay /></el-icon> 開始爬取
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 當前任務進度：採集階段 -->
    <el-card v-if="store.currentTask && store.polling" style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; align-items: center; gap: 12px">
          <span><el-icon><Loading /></el-icon> 當前任務</span>
          <el-tag :type="statusTagType(store.currentTask.status)" size="small">
            {{ store.currentTask.status_label }}
          </el-tag>
          <span style="font-size: 13px; color: #909399; margin-left: auto">
            進度 {{ store.currentTask.progress }}% | 已採集 {{ store.currentTask.total_jobs }} 條
          </span>
          <el-button size="small" @click="store.pauseTask(store.currentTask!.task_id)" :disabled="store.currentTask.status !== 'running'">
            暫停
          </el-button>
          <el-button size="small" @click="store.resumeTask(store.currentTask!.task_id)" :disabled="store.currentTask.status !== 'paused'">
            恢復
          </el-button>
          <el-button size="small" type="danger" @click="store.cancelTask(store.currentTask!.task_id)" :disabled="!['running','paused','post_processing'].includes(store.currentTask.status)">
            取消
          </el-button>
        </div>
      </template>

      <el-progress :percentage="store.currentTask.progress" :stroke-width="20" :text-inside="true" />

      <div v-if="store.currentTask.source_progress && Object.keys(store.currentTask.source_progress).length" style="margin-top: 12px">
        <div v-for="(v, k) in store.currentTask.source_progress" :key="k" style="margin-bottom: 8px">
          <span style="display: inline-block; width: 120px; font-size: 13px">{{ k }}</span>
          <el-progress
            :percentage="v.total > 0 ? Math.round(v.collected / v.total * 100) : 0"
            :stroke-width="14"
            style="display: inline-block; width: calc(100% - 130px); vertical-align: middle"
          />
          <span style="font-size: 12px; color: #909399; margin-left: 8px">{{ v.collected }}/{{ v.total || '?' }}</span>
        </div>
      </div>

      <!-- 後處理進度 -->
      <div v-if="['post_processing','processed','processing_failed'].includes(store.currentTask.status)" style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #e4e7ed">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
          <el-icon><SetUp /></el-icon>
          <span style="font-weight: 600; font-size: 14px">後處理進度</span>
          <el-tag v-if="store.currentTask.status === 'post_processing'" type="warning" size="small">執行中</el-tag>
          <el-tag v-else-if="store.currentTask.status === 'processed'" type="success" size="small">已完成</el-tag>
          <el-tag v-else-if="store.currentTask.status === 'processing_failed'" type="danger" size="small">失敗</el-tag>
        </div>

        <!-- 階段指示器 -->
        <div style="display: flex; gap: 6px; margin-bottom: 12px">
          <div
            v-for="phase in postPhases"
            :key="phase.key"
            :style="{
              flex: 1,
              textAlign: 'center',
              fontSize: '12px',
              padding: '6px 0',
              borderRadius: '4px',
              background: phaseBg(phase.key),
              color: phaseColor(phase.key),
              fontWeight: store.currentTask.post_phase === phase.key ? '600' : '400',
            }"
          >
            {{ phase.label }}
          </div>
        </div>

        <el-progress
          :percentage="overallPostPct"
          :stroke-width="18"
          :text-inside="true"
          :status="postProgressStatus"
        />

        <!-- 結果摘要 -->
        <div v-if="store.currentTask.post_result" style="margin-top: 12px; display: flex; flex-wrap: wrap; gap: 16px">
          <el-statistic title="清洗" :value="store.currentTask.post_result.cleaned_count ?? 0" />
          <el-statistic title="角色分類" :value="store.currentTask.post_result.classified_count ?? 0" />
          <el-statistic title="MongoDB" :value="store.currentTask.post_result.db_inserted ?? 0" />
          <el-statistic title="CSV 導出" :value="store.currentTask.post_result.csv_exported ?? 0" />
          <el-statistic title="向量文檔" :value="store.currentTask.post_result.vector_indexed ?? 0" />
          <el-statistic v-if="(store.currentTask.post_result.errors?.length ?? 0) > 0" title="錯誤" :value="store.currentTask.post_result.errors!.length" :value-style="{ color: '#f56c6c' }" />
        </div>
      </div>

      <!-- 即時日誌 -->
      <div style="margin-top: 12px; max-height: 200px; overflow-y: auto; background: #1e1e1e; border-radius: 6px; padding: 8px 12px; font-family: monospace; font-size: 12px">
        <div v-for="(log, i) in store.currentTask.logs" :key="i" :style="{ color: logColor(log.level) }">
          [{{ fmtTime(log.time) }}] {{ log.message }}
        </div>
        <div v-if="!store.currentTask.logs?.length" style="color: #666">等待日誌...</div>
      </div>
    </el-card>

    <!-- 歷史任務 -->
    <el-card>
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px">
          <span><el-icon><List /></el-icon> 任務記錄</span>
          <el-radio-group v-model="statusFilter" size="small" @change="handleFilterChange" style="margin-left: auto">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="running">運行中</el-radio-button>
            <el-radio-button value="post_processing">後處理中</el-radio-button>
            <el-radio-button value="processed">已完成</el-radio-button>
            <el-radio-button value="processing_failed">處理失敗</el-radio-button>
          </el-radio-group>
          <el-button size="small" @click="refreshTasks" :loading="store.loading">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </template>

      <el-table :data="store.tasks" stripe v-loading="store.loading" empty-text="暫無任務記錄">
        <el-table-column prop="task_id" label="任務 ID" width="140">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">
              {{ row.task_id }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="關鍵詞" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="kw in row.keywords" :key="kw" size="small" style="margin: 1px 2px">{{ kw }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="來源" width="160">
          <template #default="{ row }">
            <el-tag v-for="s in row.sources" :key="s" size="small" type="info" style="margin: 1px 2px">{{ s }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="狀態" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="進度" width="160">
          <template #default="{ row }">
            <template v-if="row.status === 'post_processing'">
              <div style="font-size: 11px; color: #909399; margin-bottom: 2px">{{ phaseLabel(row.post_phase) }}</div>
              <el-progress :percentage="row.post_phase_pct" :stroke-width="6" :show-text="true" />
            </template>
            <template v-else>
              <el-progress :percentage="row.progress" :stroke-width="8" :show-text="true" />
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="total_jobs" label="採集數" width="80" />
        <el-table-column label="建立時間" width="100">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-popconfirm title="確認刪除此任務?" @confirm="store.deleteTask(row.task_id)">
              <template #reference>
                <el-button link type="danger" size="small" :disabled="row.status === 'running' || row.status === 'post_processing'">刪除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 任務詳情對話框 -->
    <el-dialog v-model="detailVisible" title="任務詳情" width="700px">
      <template v-if="detailTask">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="任務 ID">{{ detailTask.task_id }}</el-descriptions-item>
          <el-descriptions-item label="狀態">
            <el-tag :type="statusTagType(detailTask.status)" size="small">{{ detailTask.status_label }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="關鍵詞">
            <el-tag v-for="kw in detailTask.keywords" :key="kw" size="small" style="margin: 1px 2px">{{ kw }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="來源">
            <el-tag v-for="s in detailTask.sources" :key="s" size="small" type="info" style="margin: 1px 2px">{{ s }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="採集進度">{{ detailTask.progress }}%</el-descriptions-item>
          <el-descriptions-item label="已採集">{{ detailTask.total_jobs }} 條</el-descriptions-item>
          <el-descriptions-item label="建立時間">{{ fmtDate(detailTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成時間">{{ detailTask.completed_at ? fmtDate(detailTask.completed_at) : '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 後處理結果摘要 -->
        <template v-if="detailTask.post_result">
          <h4 style="margin-top: 16px">後處理結果</h4>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="清洗">{{ detailTask.post_result.cleaned_count ?? 0 }} 條</el-descriptions-item>
            <el-descriptions-item label="角色分類">{{ detailTask.post_result.classified_count ?? 0 }} 條</el-descriptions-item>
            <el-descriptions-item label="技能提取">{{ detailTask.post_result.extracted_count ?? 0 }} 條</el-descriptions-item>
            <el-descriptions-item label="MongoDB 入庫">{{ detailTask.post_result.db_inserted ?? 0 }} 條</el-descriptions-item>
            <el-descriptions-item label="CSV 導出">{{ detailTask.post_result.csv_exported ?? 0 }} 條</el-descriptions-item>
            <el-descriptions-item label="向量文檔">{{ detailTask.post_result.vector_indexed ?? 0 }} 篇</el-descriptions-item>
          </el-descriptions>
          <div v-if="detailTask.post_result.phase_timings" style="margin-top: 8px; font-size: 12px; color: #909399">
            耗時：
            <span v-for="(t, phase) in detailTask.post_result.phase_timings" :key="phase" style="margin-right: 12px">
              {{ phaseLabel(String(phase)) }} {{ t }}s
            </span>
          </div>
          <div v-if="detailTask.post_result.errors?.length" style="margin-top: 8px">
            <el-alert
              v-for="(err, i) in detailTask.post_result.errors"
              :key="i"
              :title="err"
              type="error"
              :closable="false"
              style="margin-bottom: 4px"
            />
          </div>
        </template>

        <h4 style="margin-top: 16px">執行日誌</h4>
        <div style="max-height: 250px; overflow-y: auto; background: #1e1e1e; border-radius: 6px; padding: 8px 12px; font-family: monospace; font-size: 12px">
          <div v-for="(log, i) in detailTask.logs" :key="i" :style="{ color: logColor(log.level) }">
            [{{ fmtTime(log.time) }}] {{ log.message }}
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useCrawlerStore } from '@/stores/crawler'
import type { CrawlerTaskDTO, CrawlerTaskDetailDTO } from '@/api/crawler'

const store = useCrawlerStore()

const form = reactive({
  keywords: [] as string[],
  sources: [] as string[],
  post_cleaning: true,
  post_extraction: true,
  post_classification: true,
  post_kb_import: true,
  post_vector_index: true,
})
const creating = ref(false)
const statusFilter = ref('')
const detailVisible = ref(false)
const detailTask = ref<CrawlerTaskDetailDTO | null>(null)

const availableSourceOptions = [
  { label: 'JobsDB', value: 'jobsdb' },
  { label: 'JIJIS', value: 'jijis' },
  { label: 'OfferToday', value: 'offertoday' },
  { label: '科學園 (HKSTP)', value: 'hkstp' },
  { label: '數碼港 (Cyberport)', value: 'cyberport' },
  { label: 'Indeed', value: 'indeed' },
]

const postPhases = [
  { key: 'cleaning', label: '清洗' },
  { key: 'extraction', label: '提取' },
  { key: 'classification', label: '分類' },
  { key: 'kb_import', label: '知識庫' },
  { key: 'vector_index', label: '向量索引' },
]

function phaseLabel(phase: string): string {
  const map: Record<string, string> = {
    cleaning: '清洗', extraction: '技能提取', classification: '角色分類',
    kb_import: '知識庫導入', vector_index: '向量索引', done: '完成',
  }
  return map[phase] || phase
}

const phaseOrder = ['cleaning', 'extraction', 'classification', 'kb_import', 'vector_index', 'done']

const overallPostPct = computed(() => {
  const t = store.currentTask
  if (!t) return 0
  if (t.post_phase === 'done') return 100
  const idx = phaseOrder.indexOf(t.post_phase)
  if (idx < 0) return 0
  const phaseWeight = 100 / (phaseOrder.length - 1)
  return Math.min(Math.round(idx * phaseWeight + (t.post_phase_pct / 100) * phaseWeight), 100)
})

const postProgressStatus = computed(() => {
  const s = store.currentTask?.status
  if (s === 'processed') return 'success'
  if (s === 'processing_failed') return 'exception'
  return ''
})

function phaseBg(phase: string): string {
  const t = store.currentTask
  if (!t) return '#f0f2f5'
  if (t.post_phase === phase) return '#e6f4ff'
  const currentIdx = phaseOrder.indexOf(t.post_phase)
  const thisIdx = phaseOrder.indexOf(phase)
  if (thisIdx < currentIdx) return '#f0fbe6'
  return '#f0f2f5'
}

function phaseColor(phase: string): string {
  const t = store.currentTask
  if (!t) return '#909399'
  if (t.post_phase === phase) return '#409eff'
  const currentIdx = phaseOrder.indexOf(t.post_phase)
  const thisIdx = phaseOrder.indexOf(phase)
  if (thisIdx < currentIdx) return '#67c23a'
  return '#909399'
}

function statusTagType(status: string): 'info' | 'warning' | 'success' | 'danger' | '' {
  const map: Record<string, 'info' | 'warning' | 'success' | 'danger' | ''> = {
    idle: 'info', running: '', paused: 'warning',
    completed: 'warning', post_processing: 'warning',
    processed: 'success', processing_failed: 'danger',
    failed: 'danger', cancelled: 'info',
  }
  return map[status] || 'info'
}

function logColor(level: string): string {
  if (level === 'error') return '#f56c6c'
  if (level === 'warning') return '#e6a23c'
  return '#b3b3b3'
}

function fmtTime(iso: string): string {
  if (!iso) return ''
  return iso.slice(11, 19)
}

function fmtDate(iso: string): string {
  if (!iso) return ''
  return iso.slice(0, 10) + ' ' + iso.slice(11, 19)
}

async function handleCreate() {
  if (!form.keywords.length || !form.sources.length) return
  creating.value = true
  try {
    const task = await store.createTask(form.keywords, form.sources, {
      run_cleaning: form.post_cleaning,
      run_extraction: form.post_extraction,
      run_classification: form.post_classification,
      run_kb_import: form.post_kb_import,
      run_vector_index: form.post_vector_index,
    })
    store.startPolling(task.task_id)
    form.keywords = []
  } finally {
    creating.value = false
  }
}

function handleFilterChange() {
  store.fetchTasks(statusFilter.value || undefined)
}

async function showDetail(row: CrawlerTaskDTO) {
  detailTask.value = await store.fetchTaskDetail(row.task_id)
  detailVisible.value = true
}

function refreshTasks() {
  store.fetchTasks(statusFilter.value || undefined)
}

onMounted(() => {
  store.fetchTasks()
})

onUnmounted(() => {
  store.stopPolling()
})
</script>
