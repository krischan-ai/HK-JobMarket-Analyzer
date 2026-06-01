<template>
  <div style="display: flex; align-items: center; background: #409EFF; color: #fff; padding: 0 24px; height: 56px; gap: 24px">
    <div style="display: flex; align-items: center; gap: 8px; cursor: pointer" @click="$router.push('/')">
      <el-icon :size="28"><DataAnalysis /></el-icon>
      <span style="font-size: 18px; font-weight: 700">HK IT Job Analyzer</span>
    </div>

    <el-menu
      mode="horizontal"
      :default-active="route.path"
      router
      style="flex: 1; background: transparent; border: none; --el-menu-text-color: rgba(255,255,255,0.85); --el-menu-hover-bg-color: rgba(255,255,255,0.15); --el-menu-active-color: #fff"
    >
    </el-menu>

    <div style="display: flex; align-items: center; gap: 12px">
      <el-tag v-if="systemStore.healthy" type="success" size="small" effect="dark">API 已連接</el-tag>
      <el-tag v-else type="danger" size="small" effect="dark">API 離線</el-tag>
      <el-badge :value="systemStore.dataCount" type="primary">
        <el-icon :size="22"><Folder /></el-icon>
      </el-badge>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '@/stores/system'
import { DataAnalysis, Folder } from '@element-plus/icons-vue'

const route = useRoute()
const systemStore = useSystemStore()

onMounted(() => systemStore.checkHealth())
</script>
