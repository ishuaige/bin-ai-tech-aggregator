<template>
  <section class="page-shell">
    <header class="section-head">
      <h2>干货历史墙</h2>
      <p>按日期、关键字与状态筛选执行日志，查看原文与 AI 摘要。</p>
    </header>

    <section class="filter-card">
      <el-input v-model.trim="filters.keyword" placeholder="关键词（匹配原文与摘要）" clearable />
      <el-select v-model="filters.status" clearable placeholder="状态">
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-date-picker
        v-model="filters.dateRange"
        type="datetimerange"
        range-separator="至"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
      />
      <el-button type="primary" @click="search">查询</el-button>
    </section>

    <AppErrorState v-if="error" :message="error" @retry="loadLogs" />
    <AppLoadingState v-else-if="loading" />
    <AppEmptyState v-else-if="logs.length === 0" description="未检索到符合条件的执行日志。" />

    <template v-else>
      <el-table :data="logs" stripe class="data-table">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="source_id" label="来源 ID" width="100" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="执行时间" width="200">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="摘要预览" min-width="360" show-overflow-tooltip>
          <template #default="{ row }">{{ row.ai_summary || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="openDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pagination.page_size"
        :current-page="pagination.page"
        @current-change="handlePage"
      />
    </template>

    <el-drawer v-model="detailVisible" title="日志详情" size="56%">
      <AppLoadingState v-if="detailLoading" />
      <AppErrorState v-else-if="detailError" :message="detailError" @retry="retryDetail" />
      <template v-else-if="detail">
        <section class="detail-section">
          <h3>原始内容</h3>
          <pre class="raw-box">{{ detail.raw_content || '(空)' }}</pre>
        </section>
        <section class="detail-section">
          <h3>AI 摘要（Markdown 渲染）</h3>
          <article class="markdown-box" v-html="renderedMarkdown"></article>
        </section>
      </template>
    </el-drawer>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import AppLoadingState from '../components/common/AppLoadingState.vue'
import AppEmptyState from '../components/common/AppEmptyState.vue'
import AppErrorState from '../components/common/AppErrorState.vue'
import { getLogDetail, listLogs } from '../api/logs'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const loading = ref(false)
const error = ref('')
const logs = ref([])
const total = ref(0)

const filters = reactive({
  keyword: '',
  status: undefined,
  dateRange: [],
})

const pagination = reactive({
  page: 1,
  page_size: 10,
})

const detailVisible = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const detail = ref(null)
const currentDetailId = ref(null)

const renderedMarkdown = computed(() => md.render(detail.value?.ai_summary || '无摘要'))

function buildParams() {
  const params = {
    page: pagination.page,
    page_size: pagination.page_size,
  }
  if (filters.keyword) params.keyword = filters.keyword
  if (filters.status) params.status = filters.status
  if (filters.dateRange?.length === 2) {
    params.date_from = filters.dateRange[0].toISOString()
    params.date_to = filters.dateRange[1].toISOString()
  }
  return params
}

async function loadLogs() {
  loading.value = true
  error.value = ''
  try {
    const data = await listLogs(buildParams())
    logs.value = data.items
    total.value = data.meta.total
  } catch (err) {
    error.value = err?.response?.data?.message || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function handlePage(page) {
  pagination.page = page
  loadLogs()
}

function search() {
  pagination.page = 1
  loadLogs()
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

async function openDetail(logId) {
  detailVisible.value = true
  currentDetailId.value = logId
  detailLoading.value = true
  detailError.value = ''
  detail.value = null
  try {
    detail.value = await getLogDetail(logId)
  } catch (err) {
    detailError.value = err?.response?.data?.message || err.message || '加载详情失败'
  } finally {
    detailLoading.value = false
  }
}

function retryDetail() {
  if (!currentDetailId.value) return
  openDetail(currentDetailId.value)
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.page-shell {
  display: grid;
  gap: 14px;
}

.section-head h2 {
  font-size: 28px;
}

.section-head p {
  margin-top: 7px;
  color: var(--text-sub);
}

.filter-card {
  border-radius: var(--radius);
  background: rgba(11, 27, 52, 0.82);
  border: 1px solid var(--line);
  padding: 14px;
  display: grid;
  grid-template-columns: 1.3fr 0.8fr 1.6fr auto;
  gap: 10px;
  align-items: center;
}

.data-table {
  border-radius: 12px;
  overflow: hidden;
}

.pager {
  margin-top: 14px;
  justify-content: flex-end;
}

.detail-section {
  margin-bottom: 18px;
}

.detail-section h3 {
  margin-bottom: 10px;
}

.raw-box {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(9, 20, 40, 0.88);
  color: #dbe8ff;
  padding: 12px;
  white-space: pre-wrap;
  font-family: 'Source Sans 3', sans-serif;
}

.markdown-box {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(9, 20, 40, 0.88);
  padding: 12px;
  color: #dbe8ff;
  line-height: 1.62;
}

.markdown-box :deep(ul) {
  padding-left: 18px;
}

.markdown-box :deep(strong) {
  color: #48f38a;
}

:deep(.el-drawer) {
  background: #111f36;
}

:deep(.el-drawer__title),
:deep(.el-table),
:deep(.el-table th.el-table__cell),
:deep(.el-table tr),
:deep(.el-table td.el-table__cell) {
  color: var(--text-main);
}

:deep(.el-table),
:deep(.el-table th.el-table__cell),
:deep(.el-table tr),
:deep(.el-table td.el-table__cell) {
  background: rgba(14, 31, 58, 0.78);
  border-color: rgba(54, 82, 123, 0.42);
}

@media (max-width: 1080px) {
  .filter-card {
    grid-template-columns: 1fr;
  }
}
</style>
