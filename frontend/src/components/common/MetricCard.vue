<template>
  <article class="metric-card">
    <p class="label">{{ title }}</p>
    <p class="value">{{ value }}</p>
    <p class="hint">{{ hint }}</p>
  </article>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  value: {
    type: [String, Number],
    default: '-',
  },
  hint: {
    type: String,
    default: '',
  },
})
</script>

<style scoped>
.metric-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: linear-gradient(160deg, rgba(15, 34, 63, 0.95), rgba(10, 26, 50, 0.92));
  padding: 18px;
  box-shadow: var(--shadow);
  min-height: 130px;
}

.label {
  color: var(--text-sub);
  font-size: 14px;
}

.value {
  font-family: 'Lexend', sans-serif;
  font-size: 34px;
  margin-top: 14px;
  color: var(--text-main);
}

.hint {
  margin-top: 10px;
  font-size: 13px;
  color: #90a9cb;
}
</style>
