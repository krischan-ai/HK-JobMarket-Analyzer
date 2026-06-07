<template>
  <el-menu
    :default-active="route.path"
    router
    style="border: none"
    background-color="#f5f7fa"
  >
    <el-menu-item index="/dashboard">
      <el-icon><Odometer /></el-icon>
      <span>儀表盤</span>
    </el-menu-item>
    <el-menu-item index="/jobs">
      <el-icon><Document /></el-icon>
      <span>崗位瀏覽</span>
    </el-menu-item>
    <el-menu-item index="/tech-trends">
      <el-icon><TrendCharts /></el-icon>
      <span>技術趨勢</span>
    </el-menu-item>
    <el-menu-item index="/salary">
      <el-icon><Money /></el-icon>
      <span>薪資分析</span>
    </el-menu-item>
    <el-menu-item index="/location">
      <el-icon><Location /></el-icon>
      <span>區域分佈</span>
    </el-menu-item>
    <el-menu-item index="/role-classify">
      <el-icon><Aim /></el-icon>
      <span>角色分類</span>
    </el-menu-item>
    <el-menu-item-group title="知識庫">
      <el-menu-item index="/knowledge">
        <el-icon><Collection /></el-icon>
        <span>知識庫總覽</span>
      </el-menu-item>
      <el-menu-item index="/upload">
        <el-icon><Upload /></el-icon>
        <span>上傳數據</span>
      </el-menu-item>
      <el-menu-item index="/manage">
        <el-icon><Edit /></el-icon>
        <span>數據管理</span>
      </el-menu-item>
    </el-menu-item-group>
    <el-menu-item-group title="系統工具">
      <el-menu-item index="/crawler">
        <el-icon><Monitor /></el-icon>
        <span>爬蟲控制台</span>
      </el-menu-item>
      <el-menu-item index="/explore">
        <el-icon><Search /></el-icon>
        <span>數據探索</span>
      </el-menu-item>
      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <span>系統設置</span>
      </el-menu-item>
    </el-menu-item-group>
  </el-menu>
</template>

<script lang="ts" setup>
import { useRoute } from 'vue-router'
const route = useRoute()
</script>
