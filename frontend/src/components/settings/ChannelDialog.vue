<template>
  <el-dialog v-model="visible" :title="title" width="560px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-form-item label="平台" prop="platform">
        <el-select v-model="form.platform" placeholder="请选择平台">
          <el-option label="企业微信" value="wechat" />
          <el-option label="钉钉" value="dingtalk" />
          <el-option label="飞书" value="feishu" />
        </el-select>
      </el-form-item>
      <el-form-item label="渠道名称" prop="name">
        <el-input v-model.trim="form.name" maxlength="50" placeholder="例如 AI 核心前沿群" />
      </el-form-item>
      <el-form-item label="Webhook" prop="webhook_url">
        <el-input v-model.trim="form.webhook_url" maxlength="255" placeholder="https://..." />
      </el-form-item>
      <el-form-item label="启用状态" prop="is_active">
        <el-switch v-model="form.is_active" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  mode: {
    type: String,
    default: 'create',
  },
  initialData: {
    type: Object,
    default: null,
  },
})

const emits = defineEmits(['update:modelValue', 'submit'])

const formRef = ref()
const submitting = ref(false)

const form = reactive({
  platform: 'wechat',
  name: '',
  webhook_url: '',
  is_active: true,
})

const rules = {
  platform: [{ required: true, message: '请选择平台', trigger: 'change' }],
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  webhook_url: [
    { required: true, message: '请输入 Webhook 地址', trigger: 'blur' },
    { type: 'url', message: '请输入合法 URL', trigger: 'blur' },
  ],
}

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emits('update:modelValue', value),
})

const title = computed(() => (props.mode === 'edit' ? '编辑推送渠道' : '新增推送渠道'))

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    const data = props.initialData
    form.platform = data?.platform || 'wechat'
    form.name = data?.name || ''
    form.webhook_url = data?.webhook_url || ''
    form.is_active = data?.is_active ?? true
  },
)

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await emits('submit', {
      platform: form.platform,
      name: form.name,
      webhook_url: form.webhook_url,
      is_active: form.is_active,
    })
    visible.value = false
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  background: #0e203d;
}

:deep(.el-dialog) {
  background: #111f36;
  border: 1px solid var(--line);
  border-radius: 14px;
}

:deep(.el-dialog__title),
:deep(.el-form-item__label) {
  color: var(--text-main);
}
</style>
