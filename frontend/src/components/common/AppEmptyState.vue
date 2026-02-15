<template>
  <div class="state-card">
    <el-empty :description="description" />
  </div>
</template>

<script setup>
defineProps({
  description: {
    type: String,
    default: '暂无数据',
  },
})
</script>

<style scoped>
.state-card {
  border: 1px dashed var(--line);
  background: rgba(12, 28, 52, 0.78);
  border-radius: var(--radius);
  padding: 12px;
}

:deep(.el-empty__description p) {
  color: var(--text-sub);
}
</style>
