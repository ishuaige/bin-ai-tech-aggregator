<template>
  <div class="state-card">
    <el-skeleton animated :rows="4" />
  </div>
</template>

<script setup>
</script>

<style scoped>
.state-card {
  border: 1px solid var(--line);
  background: linear-gradient(165deg, rgba(16, 33, 63, 0.95), rgba(13, 29, 55, 0.85));
  border-radius: var(--radius);
  padding: 18px;
  box-shadow: var(--shadow);
}

:deep(.el-skeleton__item) {
  background: linear-gradient(90deg, rgba(24, 47, 84, 0.35), rgba(45, 82, 126, 0.62), rgba(24, 47, 84, 0.35));
}
</style>
