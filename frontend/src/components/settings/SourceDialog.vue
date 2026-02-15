<template>
  <el-dialog v-model="visible" :title="title" width="520px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-form-item label="类型" prop="type">
        <el-select v-model="form.type" placeholder="请选择类型">
          <el-option label="作者监控" value="author" />
          <el-option label="关键字监控" value="keyword" />
        </el-select>
      </el-form-item>
      <el-form-item label="监控值" prop="value">
        <el-input v-model.trim="form.value" maxlength="100" placeholder="例如 @karpathy 或 AI Agent" />
      </el-form-item>
      <el-form-item label="备注" prop="remark">
        <el-input v-model.trim="form.remark" maxlength="255" show-word-limit placeholder="可选" />
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
  type: 'author',
  value: '',
  remark: '',
  is_active: true,
})

const rules = {
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  value: [{ required: true, message: '请输入监控值', trigger: 'blur' }],
}

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emits('update:modelValue', value),
})

const title = computed(() => (props.mode === 'edit' ? '编辑监控源' : '新增监控源'))

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    const data = props.initialData
    form.type = data?.type || 'author'
    form.value = data?.value || ''
    form.remark = data?.remark || ''
    form.is_active = data?.is_active ?? true
  },
)

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await emits('submit', {
      type: form.type,
      value: form.value,
      remark: form.remark || null,
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
