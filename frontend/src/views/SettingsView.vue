<template>
  <section class="page-shell">
    <header class="section-head">
      <h2>配置中心</h2>
      <p>管理监控源、推送渠道与源-渠道绑定关系。</p>
    </header>

    <el-tabs v-model="activeTab" type="border-card" class="tabs-shell">
      <el-tab-pane label="监控源" name="sources">
        <section class="tool-row">
          <el-select v-model="sourceFilters.type" clearable placeholder="类型" @change="reloadSources">
            <el-option label="作者" value="author" />
            <el-option label="关键字" value="keyword" />
          </el-select>
          <el-select v-model="sourceFilters.is_active" clearable placeholder="状态" @change="reloadSources">
            <el-option label="启用" :value="true" />
            <el-option label="停用" :value="false" />
          </el-select>
          <el-button type="primary" @click="openSourceCreate">新增监控源</el-button>
        </section>

        <AppErrorState v-if="sourceError" :message="sourceError" @retry="loadSources" />
        <AppLoadingState v-else-if="sourceLoading" />
        <AppEmptyState v-else-if="sources.length === 0" description="暂无监控源，请先新增。" />

        <template v-else>
          <el-table :data="sources" class="data-table" stripe>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="value" label="监控值" min-width="220" />
            <el-table-column prop="remark" label="备注" min-width="180" />
            <el-table-column label="启用" width="110">
              <template #default="{ row }">
                <el-switch v-model="row.is_active" @change="toggleSource(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="openSourceEdit(row)">编辑</el-button>
                <el-button text type="danger" @click="removeSource(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="pager"
            background
            layout="total, prev, pager, next"
            :total="sourceTotal"
            :page-size="sourcePagination.page_size"
            :current-page="sourcePagination.page"
            @current-change="handleSourcePage"
          />
        </template>
      </el-tab-pane>

      <el-tab-pane label="推送渠道" name="channels">
        <section class="tool-row">
          <el-select v-model="channelFilters.platform" clearable placeholder="平台" @change="reloadChannels">
            <el-option label="企业微信" value="wechat" />
            <el-option label="钉钉" value="dingtalk" />
            <el-option label="飞书" value="feishu" />
          </el-select>
          <el-select v-model="channelFilters.is_active" clearable placeholder="状态" @change="reloadChannels">
            <el-option label="启用" :value="true" />
            <el-option label="停用" :value="false" />
          </el-select>
          <el-button type="primary" @click="openChannelCreate">新增渠道</el-button>
        </section>

        <AppErrorState v-if="channelError" :message="channelError" @retry="loadChannels" />
        <AppLoadingState v-else-if="channelLoading" />
        <AppEmptyState v-else-if="channels.length === 0" description="暂无推送渠道，请先新增。" />

        <template v-else>
          <el-table :data="channels" class="data-table" stripe>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="platform" label="平台" width="120" />
            <el-table-column prop="webhook_url" label="Webhook" min-width="260" show-overflow-tooltip />
            <el-table-column label="启用" width="110">
              <template #default="{ row }">
                <el-switch v-model="row.is_active" @change="toggleChannel(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="openChannelEdit(row)">编辑</el-button>
                <el-button text type="danger" @click="removeChannel(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="pager"
            background
            layout="total, prev, pager, next"
            :total="channelTotal"
            :page-size="channelPagination.page_size"
            :current-page="channelPagination.page"
            @current-change="handleChannelPage"
          />
        </template>
      </el-tab-pane>

      <el-tab-pane label="源-渠道绑定" name="bindings">
        <section class="tool-row">
          <el-select v-model="bindingFilters.source_id" clearable placeholder="筛选监控源" @change="reloadBindings">
            <el-option v-for="source in sourceOptions" :key="source.id" :label="source.value" :value="source.id" />
          </el-select>
          <el-select v-model="bindingFilters.channel_id" clearable placeholder="筛选推送渠道" @change="reloadBindings">
            <el-option
              v-for="channel in channelOptions"
              :key="channel.id"
              :label="`${channel.name} (${channel.platform})`"
              :value="channel.id"
            />
          </el-select>
          <el-select v-model="bindingForm.source_id" placeholder="选择监控源">
            <el-option v-for="source in sourceOptions" :key="source.id" :label="source.value" :value="source.id" />
          </el-select>
          <el-select v-model="bindingForm.channel_id" placeholder="选择渠道">
            <el-option
              v-for="channel in channelOptions"
              :key="channel.id"
              :label="`${channel.name} (${channel.platform})`"
              :value="channel.id"
            />
          </el-select>
          <el-button type="primary" @click="createBinding">新增绑定</el-button>
        </section>

        <AppErrorState v-if="bindingError" :message="bindingError" @retry="loadBindings" />
        <AppLoadingState v-else-if="bindingLoading" />
        <AppEmptyState v-else-if="bindings.length === 0" description="暂无绑定关系，默认推送到所有启用渠道。" />

        <template v-else>
          <el-table :data="bindings" class="data-table" stripe>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="监控源" min-width="240">
              <template #default="{ row }">
                <span>{{ sourceNameById(row.source_id) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="推送渠道" min-width="240">
              <template #default="{ row }">
                <span>{{ channelNameById(row.channel_id) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="180">
              <template #default="{ row }">
                <span>{{ formatTime(row.created_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button text type="danger" @click="removeBinding(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="pager"
            background
            layout="total, prev, pager, next"
            :total="bindingTotal"
            :page-size="bindingPagination.page_size"
            :current-page="bindingPagination.page"
            @current-change="handleBindingPage"
          />
        </template>
      </el-tab-pane>
    </el-tabs>

    <SourceDialog
      v-model="sourceDialog.visible"
      :mode="sourceDialog.mode"
      :initial-data="sourceDialog.current"
      @submit="saveSource"
    />

    <ChannelDialog
      v-model="channelDialog.visible"
      :mode="channelDialog.mode"
      :initial-data="channelDialog.current"
      @submit="saveChannel"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppLoadingState from '../components/common/AppLoadingState.vue'
import AppEmptyState from '../components/common/AppEmptyState.vue'
import AppErrorState from '../components/common/AppErrorState.vue'
import SourceDialog from '../components/settings/SourceDialog.vue'
import ChannelDialog from '../components/settings/ChannelDialog.vue'
import { createSource, deleteSource, listSources, updateSource } from '../api/sources'
import { createChannel, deleteChannel, listChannels, updateChannel } from '../api/channels'
import {
  createSourceChannelBinding,
  deleteSourceChannelBinding,
  listSourceChannelBindings,
} from '../api/sourceChannelBindings'

const activeTab = ref('sources')

const sourceLoading = ref(false)
const sourceError = ref('')
const sources = ref([])
const sourceTotal = ref(0)
const sourcePagination = reactive({ page: 1, page_size: 10 })
const sourceFilters = reactive({ type: undefined, is_active: undefined })
const sourceDialog = reactive({
  visible: false,
  mode: 'create',
  current: null,
})

const channelLoading = ref(false)
const channelError = ref('')
const channels = ref([])
const channelTotal = ref(0)
const channelPagination = reactive({ page: 1, page_size: 10 })
const channelFilters = reactive({ platform: undefined, is_active: undefined })
const channelDialog = reactive({
  visible: false,
  mode: 'create',
  current: null,
})

const bindingLoading = ref(false)
const bindingError = ref('')
const bindings = ref([])
const bindingTotal = ref(0)
const bindingPagination = reactive({ page: 1, page_size: 10 })
const bindingFilters = reactive({ source_id: undefined, channel_id: undefined })
const bindingForm = reactive({ source_id: undefined, channel_id: undefined })

const sourceOptions = computed(() => sources.value || [])
const channelOptions = computed(() => channels.value || [])

function buildParams(pagination, filters) {
  return {
    page: pagination.page,
    page_size: pagination.page_size,
    ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== undefined && value !== null)),
  }
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

async function loadSources() {
  sourceLoading.value = true
  sourceError.value = ''
  try {
    const data = await listSources(buildParams(sourcePagination, sourceFilters))
    sources.value = data.items
    sourceTotal.value = data.meta.total
  } catch (err) {
    sourceError.value = err?.response?.data?.message || err.message || '加载失败'
  } finally {
    sourceLoading.value = false
  }
}

async function loadChannels() {
  channelLoading.value = true
  channelError.value = ''
  try {
    const data = await listChannels(buildParams(channelPagination, channelFilters))
    channels.value = data.items
    channelTotal.value = data.meta.total
  } catch (err) {
    channelError.value = err?.response?.data?.message || err.message || '加载失败'
  } finally {
    channelLoading.value = false
  }
}

async function loadBindings() {
  bindingLoading.value = true
  bindingError.value = ''
  try {
    const data = await listSourceChannelBindings(buildParams(bindingPagination, bindingFilters))
    bindings.value = data.items
    bindingTotal.value = data.meta.total
  } catch (err) {
    bindingError.value = err?.response?.data?.message || err.message || '加载失败'
  } finally {
    bindingLoading.value = false
  }
}

function reloadSources() {
  sourcePagination.page = 1
  loadSources()
}

function reloadChannels() {
  channelPagination.page = 1
  loadChannels()
}

function reloadBindings() {
  bindingPagination.page = 1
  loadBindings()
}

function handleSourcePage(page) {
  sourcePagination.page = page
  loadSources()
}

function handleChannelPage(page) {
  channelPagination.page = page
  loadChannels()
}

function handleBindingPage(page) {
  bindingPagination.page = page
  loadBindings()
}

function openSourceCreate() {
  sourceDialog.mode = 'create'
  sourceDialog.current = null
  sourceDialog.visible = true
}

function openSourceEdit(row) {
  sourceDialog.mode = 'edit'
  sourceDialog.current = { ...row }
  sourceDialog.visible = true
}

async function saveSource(payload) {
  if (sourceDialog.mode === 'edit' && sourceDialog.current) {
    await updateSource(sourceDialog.current.id, payload)
    ElMessage.success('监控源已更新')
  } else {
    await createSource(payload)
    ElMessage.success('监控源已创建')
  }
  await loadSources()
}

async function toggleSource(row) {
  const previous = !row.is_active
  try {
    await updateSource(row.id, { is_active: row.is_active })
    ElMessage.success('监控源状态已更新')
  } catch (error) {
    row.is_active = previous
    throw error
  }
}

async function removeSource(row) {
  try {
    await ElMessageBox.confirm(`确认删除监控源「${row.value}」吗？`, '删除确认', { type: 'warning' })
    await deleteSource(row.id)
    ElMessage.success('监控源删除成功')
    await loadSources()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      throw error
    }
  }
}

function openChannelCreate() {
  channelDialog.mode = 'create'
  channelDialog.current = null
  channelDialog.visible = true
}

function openChannelEdit(row) {
  channelDialog.mode = 'edit'
  channelDialog.current = { ...row }
  channelDialog.visible = true
}

async function saveChannel(payload) {
  if (channelDialog.mode === 'edit' && channelDialog.current) {
    await updateChannel(channelDialog.current.id, payload)
    ElMessage.success('推送渠道已更新')
  } else {
    await createChannel(payload)
    ElMessage.success('推送渠道已创建')
  }
  await loadChannels()
}

async function toggleChannel(row) {
  const previous = !row.is_active
  try {
    await updateChannel(row.id, { is_active: row.is_active })
    ElMessage.success('渠道状态已更新')
  } catch (error) {
    row.is_active = previous
    throw error
  }
}

async function removeChannel(row) {
  try {
    await ElMessageBox.confirm(`确认删除渠道「${row.name}」吗？`, '删除确认', { type: 'warning' })
    await deleteChannel(row.id)
    ElMessage.success('渠道删除成功')
    await loadChannels()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      throw error
    }
  }
}

function sourceNameById(sourceId) {
  const source = sourceOptions.value.find((item) => item.id === sourceId)
  if (!source) return `#${sourceId}`
  return `${source.value} (${source.type})`
}

function channelNameById(channelId) {
  const channel = channelOptions.value.find((item) => item.id === channelId)
  if (!channel) return `#${channelId}`
  return `${channel.name} (${channel.platform})`
}

async function createBinding() {
  if (!bindingForm.source_id || !bindingForm.channel_id) {
    ElMessage.warning('请选择监控源和推送渠道')
    return
  }
  await createSourceChannelBinding({
    source_id: bindingForm.source_id,
    channel_id: bindingForm.channel_id,
  })
  ElMessage.success('绑定创建成功')
  await loadBindings()
}

async function removeBinding(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除绑定「${sourceNameById(row.source_id)} -> ${channelNameById(row.channel_id)}」吗？`,
      '删除确认',
      { type: 'warning' },
    )
    await deleteSourceChannelBinding(row.id)
    ElMessage.success('绑定删除成功')
    await loadBindings()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      throw error
    }
  }
}

onMounted(async () => {
  await Promise.all([loadSources(), loadChannels()])
  await loadBindings()
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

.tabs-shell {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(11, 27, 52, 0.86);
}

.tool-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.data-table {
  border-radius: 12px;
  overflow: hidden;
}

.pager {
  margin-top: 14px;
  justify-content: flex-end;
}

:deep(.el-tabs__header) {
  background: rgba(15, 34, 63, 0.5);
  border-bottom: 1px solid var(--line);
}

:deep(.el-tabs__item) {
  color: var(--text-sub);
}

:deep(.el-tabs__item.is-active) {
  color: #48f38a;
}

:deep(.el-select__wrapper) {
  min-width: 120px;
  background: rgba(13, 30, 57, 0.72);
}

:deep(.el-table),
:deep(.el-table th.el-table__cell),
:deep(.el-table tr),
:deep(.el-table td.el-table__cell) {
  background: rgba(14, 31, 58, 0.78);
  color: var(--text-main);
  border-color: rgba(54, 82, 123, 0.42);
}

@media (max-width: 900px) {
  .tool-row {
    flex-direction: column;
  }
}
</style>
