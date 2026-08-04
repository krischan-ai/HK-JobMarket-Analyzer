<template>
  <div class="resume-generate-page">
    <div class="page-heading">
      <div>
        <h2>簡歷生成</h2>
        <p>基於本地香港 IT 崗位知識庫，從真實經歷中選材並生成目標崗位簡歷。</p>
      </div>
      <el-tag type="primary" effect="plain">Evidence-first</el-tag>
    </div>

    <div class="workspace">
      <GenerateInput />
      <GenerateResult />
    </div>
  </div>
</template>

<script lang="ts" setup>
import GenerateInput from '@/components/resume-generate/GenerateInput.vue'
import GenerateResult from '@/components/resume-generate/GenerateResult.vue'
</script>

<style scoped>
.resume-generate-page {
  min-height: 100%;
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

h2 {
  margin: 0;
}

p {
  margin: 6px 0 0;
  color: #606266;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(360px, 0.9fr) minmax(460px, 1.1fr);
  gap: 16px;
  align-items: start;
}

@media (max-width: 1100px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}
</style>
