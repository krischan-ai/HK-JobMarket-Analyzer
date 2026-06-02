<template>
  <el-row :gutter="16" style="margin-bottom: 16px">
    <el-col :span="span" v-for="(card, i) in cards" :key="i">
      <StatCard :label="card.label" :value="card.value" :color="card.color || '#409EFF'" />
    </el-col>
  </el-row>
</template>

<script lang="ts" setup>
import StatCard from './StatCard.vue'

interface CardItem {
  label: string
  value: string | number
  color?: string
}

withDefaults(defineProps<{
  cards: CardItem[]
  span?: number
}>(), {
  span: 4,
})
</script>
