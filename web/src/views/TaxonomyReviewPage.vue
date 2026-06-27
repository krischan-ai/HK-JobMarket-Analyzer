<template>
  <div class="taxonomy-review-page">
    <div class="page-header">
      <div>
        <h2>词库候选审核</h2>
        <p>角色分类发现的候选标签在此确认、合并别名或拒绝；高频低风险候选可一键自动晋升。</p>
      </div>
      <div class="header-actions">
        <el-button :loading="loading" @click="reload">刷新</el-button>
        <el-button @click="previewAutoPromote">预览自动晋升</el-button>
        <el-button type="primary" :loading="promoting" @click="runAutoPromote">执行自动晋升</el-button>
      </div>
    </div>

    <el-row :gutter="12" class="stat-row">
      <el-col :span="6"><el-statistic title="候选池" :value="overview.counts.candidates" /></el-col>
      <el-col :span="6"><el-statistic title="已晋升" :value="overview.counts.promoted" /></el-col>
      <el-col :span="6"><el-statistic title="别名" :value="overview.counts.aliases" /></el-col>
      <el-col :span="6"><el-statistic title="已拒绝" :value="overview.counts.rejections" /></el-col>
    </el-row>

    <el-card>
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="`候选池 (${overview.counts.candidates})`" name="candidates">
          <el-table :data="overview.candidates" stripe v-loading="loading">
            <el-table-column prop="name" label="标签" min-width="180" />
            <el-table-column prop="category" label="分类" width="160">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.category }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="support_count" label="支持岗位" width="100" sortable />
            <el-table-column prop="confidence_avg" label="平均置信" width="100" sortable />
            <el-table-column label="证据" min-width="260">
              <template #default="{ row }">
                <div class="evidence-cell">
                  <span v-for="(ev, i) in row.evidence_samples.slice(0, 2)" :key="i">{{ ev }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" @click="confirm(row)">确认</el-button>
                <el-button size="small" @click="openMerge(row)">合并别名</el-button>
                <el-button size="small" type="danger" @click="reject(row)">拒绝</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty description="暂无候选标签；在角色分类页完成「分类全部」后会自动沉淀候选。" :image-size="80" />
            </template>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="`已晋升 (${overview.counts.promoted})`" name="promoted">
          <el-table :data="overview.promoted" stripe>
            <el-table-column prop="name" label="标签" min-width="180" />
            <el-table-column prop="category" label="分类" width="160" />
            <el-table-column prop="support_count" label="支持岗位" width="100" sortable />
            <el-table-column prop="confidence_avg" label="平均置信" width="100" />
            <el-table-column prop="promoted_by" label="晋升方式" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.promoted_by === 'auto' ? 'warning' : 'success'">
                  {{ row.promoted_by === 'auto' ? '自动' : '人工' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="promoted_at" label="晋升时间" min-width="200" />
            <template #empty><el-empty description="暂无已晋升标签" :image-size="80" /></template>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="`别名 (${overview.counts.aliases})`" name="aliases">
          <el-table :data="overview.aliases" stripe>
            <el-table-column prop="alias" label="别名" min-width="180" />
            <el-table-column prop="canonical" label="正式标签" min-width="180" />
            <el-table-column prop="category" label="分类" width="160" />
            <el-table-column prop="evidence" label="证据" min-width="220" />
            <template #empty><el-empty description="暂无别名映射" :image-size="80" /></template>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="`已拒绝 (${overview.counts.rejections})`" name="rejections">
          <el-table :data="overview.rejections" stripe>
            <el-table-column prop="name" label="标签" min-width="180" />
            <el-table-column prop="category" label="分类" width="160" />
            <el-table-column prop="reason" label="拒绝原因" min-width="220" />
            <el-table-column prop="rejected_at" label="拒绝时间" min-width="200" />
            <template #empty><el-empty description="暂无拒绝记录" :image-size="80" /></template>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="mergeVisible" title="合并为正式标签别名" width="460px">
      <el-form label-width="92px">
        <el-form-item label="别名"><el-input v-model="mergeForm.alias" disabled /></el-form-item>
        <el-form-item label="正式标签">
          <el-input v-model="mergeForm.canonical" placeholder="映射到的正式标签名" />
        </el-form-item>
        <el-form-item label="分类"><el-input v-model="mergeForm.category" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mergeVisible = false">取消</el-button>
        <el-button type="primary" @click="submitMerge">合并</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { taxonomyApi, type TaxonomyCandidate, type TaxonomyOverview } from '@/api/taxonomy'

const emptyOverview: TaxonomyOverview = {
  candidates: [], promoted: [], aliases: [], rejections: [],
  counts: { candidates: 0, promoted: 0, aliases: 0, rejections: 0 },
}

const overview = ref<TaxonomyOverview>({ ...emptyOverview })
const loading = ref(false)
const promoting = ref(false)
const activeTab = ref('candidates')

const mergeVisible = ref(false)
const mergeForm = reactive({ alias: '', canonical: '', category: '' })

onMounted(reload)

async function reload() {
  loading.value = true
  try {
    overview.value = await taxonomyApi.overview()
  } catch {
    ElMessage.error('加载候选词库失败')
  } finally {
    loading.value = false
  }
}

async function confirm(row: TaxonomyCandidate) {
  try {
    await taxonomyApi.confirm(row.name)
    ElMessage.success(`已确认晋升：${row.name}`)
    await reload()
  } catch {
    ElMessage.error('确认失败')
  }
}

async function reject(row: TaxonomyCandidate) {
  try {
    const { value } = await ElMessageBox.prompt('请输入拒绝原因（可选）', `拒绝候选：${row.name}`, {
      confirmButtonText: '拒绝',
      cancelButtonText: '取消',
      inputPlaceholder: '如：福利语境误判 / 一次性项目描述',
    })
    await taxonomyApi.reject(row.name, value || '')
    ElMessage.success(`已拒绝：${row.name}`)
    await reload()
  } catch {
    /* 用户取消 */
  }
}

function openMerge(row: TaxonomyCandidate) {
  mergeForm.alias = row.name
  mergeForm.canonical = ''
  mergeForm.category = row.category
  mergeVisible.value = true
}

async function submitMerge() {
  if (!mergeForm.canonical.trim()) {
    ElMessage.warning('请填写正式标签名')
    return
  }
  try {
    await taxonomyApi.mergeAlias(mergeForm.alias, mergeForm.canonical, mergeForm.category)
    ElMessage.success('已合并别名')
    mergeVisible.value = false
    await reload()
  } catch {
    ElMessage.error('合并失败')
  }
}

async function previewAutoPromote() {
  try {
    const res = await taxonomyApi.autoPromote(true)
    const names = (res.eligible || []).map((r: { name: string }) => r.name)
    if (!names.length) {
      ElMessage.info('当前没有满足自动晋升条件的候选（support≥3、≥2 公司、置信≥0.85）')
    } else {
      ElMessage.success(`预览：${names.length} 个候选可晋升 — ${names.join('、')}`)
    }
  } catch {
    ElMessage.error('预览失败')
  }
}

async function runAutoPromote() {
  promoting.value = true
  try {
    const res = await taxonomyApi.autoPromote(false)
    ElMessage.success(`已自动晋升 ${res.promoted_count} 个候选`)
    await reload()
  } catch {
    ElMessage.error('自动晋升失败')
  } finally {
    promoting.value = false
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.page-header h2 { margin: 0; }
.page-header p { margin: 6px 0 0; color: #606266; font-size: 14px; }
.header-actions { display: flex; gap: 8px; flex-shrink: 0; }
.stat-row { margin-bottom: 16px; }
.evidence-cell { display: flex; flex-direction: column; gap: 4px; }
.evidence-cell span {
  font-size: 12px; color: #606266; line-height: 1.4;
  background: #f5f7fa; padding: 3px 6px; border-radius: 4px; word-break: break-word;
}
</style>
