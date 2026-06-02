<template>
  <el-table
    :data="data"
    :stripe="stripe"
    :max-height="maxHeight"
    v-loading="loading"
    :empty-text="emptyText"
  >
    <slot />
  </el-table>
  <div style="margin-top: 16px; display: flex; justify-content: center" v-if="showPagination">
      <el-pagination
        :current-page="page"
        :page-size="size"
        :total="total"
        :page-sizes="pageSizes"
        layout="total, sizes, prev, pager, next"
        @current-change="(p: number) => $emit('pageChange', p, size)"
        @size-change="(s: number) => $emit('pageChange', 1, s)"
      />
  </div>
</template>

<script lang="ts" setup>
withDefaults(defineProps<{
  data: Record<string, any>[]
  loading?: boolean
  maxHeight?: number | string
  stripe?: boolean
  emptyText?: string
  showPagination?: boolean
  page?: number
  size?: number
  total?: number
  pageSizes?: number[]
}>(), {
  loading: false,
  maxHeight: 500,
  stripe: true,
  emptyText: '暫無數據',
  showPagination: false,
  page: 1,
  size: 20,
  total: 0,
  pageSizes: () => [10, 20, 50],
})

defineEmits<{
  (e: 'pageChange', page: number, size: number): void
}>()
</script>
