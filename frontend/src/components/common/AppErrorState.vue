<template>
  <div class="state-card">
    <el-result icon="error" title="请求失败" :sub-title="message">
      <template #extra>
        <el-button type="primary" @click="$emit('retry')">重试</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup>
defineEmits(['retry'])

defineProps({
  message: {
    type: String,
    default: '请检查网络或后端服务状态。',
  },
})
</script>

<style scoped>
.state-card {
  border: 1px solid rgba(239, 68, 68, 0.45);
  background: rgba(50, 18, 18, 0.36);
  border-radius: var(--radius);
  padding: 8px;
}

:deep(.el-result__title p) {
  color: var(--text-main);
}

:deep(.el-result__subtitle p) {
  color: var(--text-sub);
}
</style>
