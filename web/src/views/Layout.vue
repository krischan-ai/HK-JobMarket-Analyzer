<template>
  <el-container style="height: 100vh">
    <el-header style="height: auto; padding: 0">
      <AppHeader />
    </el-header>
    <el-container>
      <el-aside width="220px" style="background: #f5f7fa; border-right: 1px solid #e4e7ed; overflow-y: auto">
        <AppSidebar />
      </el-aside>
      <el-main style="background: #f0f2f5; padding: 20px">
        <router-view />
      </el-main>
    </el-container>
    <el-footer style="height: auto; padding: 8px 0; text-align: center; font-size: 12px; color: #909399; border-top: 1px solid #e4e7ed">
      HK-JobMarket-Analyzer v1.7 &copy; 2026
    </el-footer>
  </el-container>
</template>

<script lang="ts" setup>
import AppHeader from '@/components/AppHeader.vue'
import AppSidebar from '@/components/AppSidebar.vue'
</script>
