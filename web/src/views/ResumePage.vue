<template>
  <div class="resume-page">
    <div class="page-heading">
      <div>
        <h2>簡歷潤色</h2>
        <p>根據目標 JD 分析技能差距，生成逐段修改建議和匹配評分。</p>
      </div>
      <el-tag type="success" effect="plain">香港 IT 市場</el-tag>
    </div>

    <div class="workspace">
      <ResumeInput />
      <ResumeResult />
    </div>
  </div>
</template>

<script lang="ts" setup>
import ResumeInput from '@/components/resume/ResumeInput.vue'
import ResumeResult from '@/components/resume/ResumeResult.vue'
</script>

<style scoped>
.resume-page {
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
  grid-template-columns: minmax(360px, 0.9fr) minmax(420px, 1.1fr);
  gap: 16px;
  align-items: stretch;
}

@media (max-width: 1100px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}
</style>
