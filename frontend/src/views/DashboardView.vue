<template>
  <section class="page-shell">
    <header class="section-head">
      <div>
        <h2>运行概览</h2>
        <p>实时查看抓取、执行与 token 消耗估算。</p>
      </div>
      <el-button type="success" :loading="runLoading" @click="handleRunNow">立即执行</el-button>
    </header>

    <AppErrorState v-if="error" :message="error" @retry="loadOverview" />
    <AppLoadingState v-else-if="loading" />

    <template v-else>
      <div class="metrics-grid">
        <MetricCard title="今日抓取量" :value="overview.today_fetch_count" hint="来源于 push_log_items" />
        <MetricCard title="今日执行次数" :value="overview.today_run_count" hint="批次触发总量" />
        <MetricCard title="今日成功次数" :value="overview.today_success_count" hint="状态 success" />
        <MetricCard title="Token 估算" :value="overview.token_estimate" hint="按条目量粗估" />
      </div>

      <div class="status-card">
        <h3>最近一次执行</h3>
        <div class="status-row">
          <span>状态</span>
          <el-tag :type="statusType">{{ overview.latest_run_status || 'none' }}</el-tag>
        </div>
        <div class="status-row">
          <span>时间</span>
          <span>{{ formatTime(overview.latest_run_at) }}</span>
        </div>
      </div>

      <div v-if="jobState" class="status-card slim">
        <h3>手动执行反馈</h3>
        <div class="status-row">
          <span>任务 ID</span>
          <span>{{ jobState.job_id }}</span>
        </div>
        <div class="status-row">
          <span>状态</span>
          <el-tag :type="jobTagType">{{ jobState.status }}</el-tag>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import MetricCard from '../components/common/MetricCard.vue'
import AppLoadingState from '../components/common/AppLoadingState.vue'
import AppErrorState from '../components/common/AppErrorState.vue'
import { fetchOverview } from '../api/dashboard'
import { fetchRunNowStatus, runNowJob } from '../api/jobs'

const loading = ref(false)
const runLoading = ref(false)
const error = ref('')
const timer = ref(null)

const overview = reactive({
  today_fetch_count: 0,
  today_run_count: 0,
  today_success_count: 0,
  latest_run_status: 'none',
  latest_run_at: null,
  token_estimate: 0,
})

const jobState = ref(null)

const statusType = computed(() => {
  if (overview.latest_run_status === 'success') return 'success'
  if (overview.latest_run_status === 'failed') return 'danger'
  return 'info'
})

const jobTagType = computed(() => {
  if (!jobState.value) return 'info'
  if (jobState.value.status === 'done') return 'success'
  if (jobState.value.status === 'failed') return 'danger'
  return 'warning'
})

async function loadOverview() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchOverview()
    Object.assign(overview, data)
  } catch (err) {
    error.value = err?.response?.data?.message || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

async function handleRunNow() {
  runLoading.value = true
  try {
    const created = await runNowJob()
    jobState.value = created
    startPolling(created.job_id)
    ElMessage.success('任务已受理，正在后台执行')
  } finally {
    runLoading.value = false
  }
}

function stopPolling() {
  if (!timer.value) return
  clearInterval(timer.value)
  timer.value = null
}

function startPolling(jobId) {
  stopPolling()
  let retry = 0
  timer.value = setInterval(async () => {
    try {
      retry += 1
      const state = await fetchRunNowStatus(jobId)
      jobState.value = state
      if (state.status === 'done' || state.status === 'failed' || retry >= 30) {
        stopPolling()
        await loadOverview()
      }
    } catch {
      if (retry >= 30) {
        stopPolling()
      }
    }
  }, 2000)
}

onMounted(() => {
  loadOverview()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.page-shell {
  display: grid;
  gap: 16px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.section-head h2 {
  font-size: 28px;
}

.section-head p {
  margin-top: 6px;
  color: var(--text-sub);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.status-card {
  border-radius: var(--radius);
  background: rgba(11, 27, 52, 0.82);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  padding: 18px;
}

.status-card h3 {
  font-size: 20px;
  margin-bottom: 12px;
}

.status-row {
  display: flex;
  justify-content: space-between;
  color: var(--text-sub);
  border-top: 1px dashed rgba(123, 162, 209, 0.26);
  padding: 11px 0;
}

.status-row span:last-child {
  color: var(--text-main);
}

.slim {
  padding-top: 14px;
}

@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .section-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
