<template>
  <el-card>
    <template #header><strong>處理結果</strong></template>
    <el-row :gutter="16">
      <el-col :span="4">
        <el-statistic title="總記錄" :value="result.total" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="成功" :value="result.success" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="跳過" :value="result.skipped" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="新增" :value="result.new_records" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="耗時(ms)" :value="result.duration_ms" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="錯誤" :value="result.errors?.length || 0" />
      </el-col>
    </el-row>
    <el-alert
      v-for="(e, i) in (result.errors || [])"
      :key="i"
      :title="e"
      type="error"
      style="margin-top: 8px"
    />
  </el-card>
</template>

<script lang="ts" setup>
import type { UploadResult } from '@/types'

defineProps<{
  result: UploadResult
}>()
</script>
