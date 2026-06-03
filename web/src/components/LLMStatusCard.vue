<template>
  <el-card v-if="status">
    <template #header><strong>LLM 分類狀態</strong></template>
    <el-row :gutter="16">
      <el-col :span="8">
        <div style="text-align: center">
          <div style="font-size: 28px; font-weight: 700; color: #409EFF">{{ status.classified }}</div>
          <div style="font-size: 13px; color: #909399; margin-top: 4px">已分類</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div style="text-align: center">
          <div style="font-size: 28px; font-weight: 700" :style="{ color: status.coverage_rate > 80 ? '#67C23A' : '#E6A23C' }">
            {{ status.coverage_rate }}%
          </div>
          <div style="font-size: 13px; color: #909399; margin-top: 4px">覆蓋率</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div style="text-align: center">
          <el-tag :type="status.llm_available ? 'success' : 'info'" size="small">{{ status.llm_available ? 'LLM 可用' : 'LLM 離線' }}</el-tag>
          <div style="font-size: 12px; color: #909399; margin-top: 8px" v-if="status.last_analysis">
            最後分析: {{ fmtDate(status.last_analysis) }}
          </div>
        </div>
      </el-col>
    </el-row>
    <div style="margin-top: 16px; text-align: center">
      <el-button type="primary" size="small" :loading="classifying" @click="$emit('run')">
        {{ classifying ? '分類中...' : (status.llm_available ? 'LLM 分類' : '規則分類') }}
      </el-button>
    </div>
  </el-card>
</template>

<script lang="ts" setup>
import type { LLMClassificationStatus } from '@/types'

defineProps<{
  status: LLMClassificationStatus
  classifying?: boolean
}>()

defineEmits<{
  (e: 'run'): void
}>()

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-HK', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}
</script>
