<template>
  <el-card>
    <el-upload
      drag
      :auto-upload="false"
      :on-change="handleChange"
      :limit="1"
      :accept="accept"
    >
      <el-icon :size="48"><UploadFilled /></el-icon>
      <div style="margin-top: 12px">拖拽或點擊上傳 {{ acceptLabel }} 文件</div>
      <template #tip>
        <div style="margin-top: 8px">{{ tip }}</div>
      </template>
    </el-upload>
  </el-card>
</template>

<script lang="ts" setup>
import type { UploadFile } from 'element-plus'

withDefaults(defineProps<{
  accept?: string
  acceptLabel?: string
  tip?: string
}>(), {
  accept: '.csv,.json,.xlsx',
  acceptLabel: 'CSV / JSON / Excel',
  tip: '支援格式: CSV (UTF-8), JSON, Excel (.xlsx)',
})

const emit = defineEmits<{
  (e: 'fileChange', file: File): void
}>()

function handleChange(f: UploadFile) {
  if (f.raw) emit('fileChange', f.raw)
}
</script>
