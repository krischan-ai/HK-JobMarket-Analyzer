<template>
  <el-card shadow="hover">
    <div style="text-align: center">
      <div :style="{ fontSize: '28px', fontWeight: 700, color: color }">{{ value }}</div>
      <div style="font-size: 13px; color: #909399; margin-top: 4px">{{ label }}</div>
    </div>
  </el-card>
</template>

<script lang="ts" setup>
withDefaults(defineProps<{
  label: string
  value: string | number
  color?: string
}>(), {
  color: '#409EFF',
})
</script>
