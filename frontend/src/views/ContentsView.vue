<template>
  <section class="page-shell">
    <header class="section-head">
      <h2>资讯列表</h2>
      <p>按发布时间倒序展示所有资讯，含基础字段与 AI 分析信息。</p>
    </header>

    <section class="filter-card">
      <el-input v-model.trim="filters.keyword" clearable placeholder="关键词（标题/正文/作者/摘要）" />
      <el-input v-model.trim="filters.platform" clearable placeholder="平台，例如 twitter" />
      <el-select v-model="filters.ai_status" clearable placeholder="AI 状态">
        <el-option label="success" value="success" />
        <el-option label="degraded" value="degraded" />
        <el-option label="failed" value="failed" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
    </section>

    <AppErrorState v-if="error" :message="error" @retry="loadContents" />
    <AppLoadingState v-else-if="loading" />
    <AppEmptyState v-else-if="items.length === 0" description="暂无资讯数据。" />

    <template v-else>
      <div class="list-grid">
        <article v-for="item in items" :key="item.id" class="content-card">
          <header class="card-head">
            <div class="title-wrap">
              <h3>{{ item.title || '(无标题)' }}</h3>
              <p class="meta-line">
                #{{ item.id }} · {{ item.platform }} · {{ item.source_type }} · 热度 {{ item.hotness }}
              </p>
            </div>
            <el-tag :type="item.ai ? aiTagType(item.ai.status) : 'info'">
              {{ item.ai ? item.ai.status : 'no_ai' }}
            </el-tag>
          </header>
          <div class="action-row">
            <el-button
              size="small"
              type="primary"
              :loading="analyzingMap[item.id] === true"
              @click="handleAnalyze(item)"
            >
              AI重分析
            </el-button>
          </div>

          <p class="meta-line">
            作者：{{ item.author_name || '-' }}
          </p>
          <p class="meta-line">
            发布时间：{{ formatTime(item.published_at) }}
          </p>
          <p class="meta-line">
            入库时间：{{ formatTime(item.created_at) }}
          </p>

          <p class="content-text">{{ item.content_text || '-' }}</p>

          <a class="link" :href="item.url" target="_blank" rel="noopener noreferrer">打开原文</a>

          <section class="ai-box">
            <h4>AI 信息</h4>
            <template v-if="item.ai">
              <p class="meta-line">模型：{{ item.ai.model }} · 评分：{{ item.ai.ai_score }}</p>
              <p class="meta-line">分析更新时间：{{ formatTime(item.ai.updated_at) }}</p>
              <p v-if="item.ai.failure_reason" class="meta-line danger">
                失败原因：{{ item.ai.failure_reason }}
              </p>
              <pre class="summary">{{ item.ai.summary || '-' }}</pre>
            </template>
            <p v-else class="meta-line">暂无 AI 分析</p>
          </section>
        </article>
      </div>

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
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppLoadingState from '../components/common/AppLoadingState.vue'
import AppEmptyState from '../components/common/AppEmptyState.vue'
import AppErrorState from '../components/common/AppErrorState.vue'
import { analyzeContent, listContents } from '../api/contents'

const loading = ref(false)
const error = ref('')
const items = ref([])
const total = ref(0)
const analyzingMap = reactive({})

const filters = reactive({
  keyword: '',
  platform: '',
  ai_status: undefined,
})

const pagination = reactive({
  page: 1,
  page_size: 10,
})

function buildParams() {
  const params = {
    page: pagination.page,
    page_size: pagination.page_size,
  }
  if (filters.keyword) params.keyword = filters.keyword
  if (filters.platform) params.platform = filters.platform
  if (filters.ai_status) params.ai_status = filters.ai_status
  return params
}

async function loadContents() {
  loading.value = true
  error.value = ''
  try {
    const data = await listContents(buildParams())
    items.value = data.items
    total.value = data.meta.total
  } catch (err) {
    error.value = err?.response?.data?.message || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function search() {
  pagination.page = 1
  loadContents()
}

function handlePage(page) {
  pagination.page = page
  loadContents()
}

function aiTagType(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'degraded') return 'warning'
  return 'info'
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

async function handleAnalyze(item) {
  analyzingMap[item.id] = true
  try {
    const updated = await analyzeContent(item.id)
    const index = items.value.findIndex((row) => row.id === item.id)
    if (index >= 0) {
      items.value[index] = updated
    }
    ElMessage.success('该条资讯 AI 分析已更新')
  } finally {
    analyzingMap[item.id] = false
  }
}

onMounted(() => {
  loadContents()
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
  grid-template-columns: 1.6fr 1fr 1fr auto;
  gap: 10px;
  align-items: center;
}

.list-grid {
  display: grid;
  gap: 12px;
}

.content-card {
  border-radius: var(--radius);
  background: rgba(11, 27, 52, 0.84);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  padding: 14px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.title-wrap h3 {
  font-size: 20px;
  margin-bottom: 6px;
}

.meta-line {
  color: var(--text-sub);
  font-size: 14px;
  margin-top: 6px;
}

.action-row {
  margin-top: 10px;
}

.content-text {
  margin-top: 10px;
  line-height: 1.55;
  color: var(--text-main);
  white-space: pre-wrap;
}

.link {
  display: inline-block;
  margin-top: 10px;
  color: #6ad8ff;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.ai-box {
  margin-top: 12px;
  border-top: 1px dashed rgba(123, 162, 209, 0.26);
  padding-top: 10px;
}

.ai-box h4 {
  font-size: 16px;
}

.summary {
  margin-top: 8px;
  padding: 10px;
  border: 1px solid var(--line);
  background: rgba(9, 20, 40, 0.88);
  border-radius: 10px;
  white-space: pre-wrap;
  color: #dbe8ff;
}

.danger {
  color: #ffb9b9;
}

.pager {
  justify-content: flex-end;
}

@media (max-width: 1080px) {
  .filter-card {
    grid-template-columns: 1fr;
  }
}
</style>
