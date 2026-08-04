<template>
  <el-container style="height: 100vh">
    <el-header style="height: auto; padding: 0">
      <AppHeader />
    </el-header>
    <el-container>
      <el-aside :width="isCollapse ? '64px' : '220px'" class="layout-aside">
        <AppSidebar :collapse="isCollapse" />
      </el-aside>
      <!-- 折叠按钮：fixed 定位，跟随视口垂直居中，不受 aside 滚动和裁剪影响 -->
      <div
        class="sidebar-toggle"
        :style="{ left: isCollapse ? '64px' : '220px' }"
        @click="toggleCollapse"
      >
        <el-icon :size="16">
          <Fold v-if="!isCollapse" />
          <Expand v-else />
        </el-icon>
      </div>
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
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppSidebar from '@/components/AppSidebar.vue'

const route = useRoute()
const isCollapse = ref(false)

// 进入岗位浏览页时自动折叠侧边栏
watch(
  () => route.path,
  (path) => {
    if (path === '/jobs') {
      isCollapse.value = true
    }
  },
  { immediate: true }
)

function toggleCollapse() {
  isCollapse.value = !isCollapse.value
}
</script>

<style scoped>
.layout-aside {
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.28s ease;
}
.sidebar-toggle {
  position: fixed;
  top: 50vh;
  transform: translate(-50%, -50%);
  width: 24px;
  height: 48px;
  background: #409eff;
  color: #fff;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  transition: left 0.28s ease, background 0.2s;
}
.sidebar-toggle:hover {
  background: #66b1ff;
}
</style>
