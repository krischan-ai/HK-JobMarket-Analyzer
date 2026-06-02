<template>
  <el-skeleton :rows="rows" animated v-if="loading" />
</template>

<script lang="ts" setup>
withDefaults(defineProps<{
  loading?: boolean
  rows?: number
}>(), {
  loading: false,
  rows: 6,
})
</script>
