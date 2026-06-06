import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: '/dashboard', name: 'Dashboard', component: () => import('@/views/DashboardPage.vue'), meta: { title: '儀表盤' } },
      { path: '/tech-trends', name: 'TechTrends', component: () => import('@/views/TechTrendsPage.vue'), meta: { title: '技術趨勢' } },
      { path: '/salary', name: 'SalaryAnalysis', component: () => import('@/views/SalaryAnalysisPage.vue'), meta: { title: '薪資分析' } },
      { path: '/location', name: 'Location', component: () => import('@/views/LocationPage.vue'), meta: { title: '區域分佈' } },
      { path: '/knowledge', name: 'KnowledgeBase', component: () => import('@/views/KnowledgeBasePage.vue'), meta: { title: '知識庫' } },
      { path: '/upload', name: 'Upload', component: () => import('@/views/UploadPage.vue'), meta: { title: '上傳數據' } },
      { path: '/manage', name: 'Manage', component: () => import('@/views/ManagePage.vue'), meta: { title: '數據管理' } },
      { path: '/explore', name: 'Explore', component: () => import('@/views/ExplorePage.vue'), meta: { title: '數據探索' } },
      { path: '/role-classify', name: 'RoleClassify', component: () => import('@/views/RoleClassificationPage.vue'), meta: { title: '角色分類' } },
      { path: '/settings', name: 'Settings', component: () => import('@/views/SettingsPage.vue'), meta: { title: '系統設置' } },
      { path: '/crawler', name: 'Crawler', component: () => import('@/views/CrawlerDashboardPage.vue'), meta: { title: '爬蟲控制台' } },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
