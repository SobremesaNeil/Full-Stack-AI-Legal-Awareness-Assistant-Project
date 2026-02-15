<template>
  <v-sheet class="bg-transparent">
    <v-expand-transition>
      <div v-if="previewUrl || isRecording" class="mb-2 px-2 d-flex align-center">
        <v-chip v-if="previewUrl" closable @click:close="clearFile" class="mr-2">
           <v-icon start icon="mdi-image"></v-icon> 已选图片
        </v-chip>
        <v-chip v-if="isRecording" color="error" variant="flat" class="animate-pulse">
           <v-icon start icon="mdi-microphone"></v-icon> 正在录音...
        </v-chip>
      </div>
    </v-expand-transition>

    <v-card elevation="4" rounded="xl" class="d-flex align-end pa-2 border">
      <v-btn icon variant="text" color="grey-darken-1" class="mb-1" @click="triggerFileInput">
        <v-icon icon="mdi-paperclip"></v-icon>
        <v-tooltip activator="parent" location="top">上传图片</v-tooltip>
      </v-btn>
      <input type="file" ref="fileInput" accept="image/*" style="display: none" @change="handleFileChange" />

      <v-textarea
        v-model="message"
        placeholder="输入法律问题，Shift + Enter 换行..."
        variant="plain"
        auto-grow
        rows="1"
        max-rows="5"
        hide-details
        class="flex-grow-1 mx-2 custom-textarea"
        @keydown.enter.exact.prevent="sendMessage"
      ></v-textarea>

      <v-menu location="top">
        <template v-slot:activator="{ props }">
          <v-btn icon variant="text" color="grey-darken-1" class="mb-1" v-bind="props">
            <v-icon icon="mdi-microphone-outline"></v-icon>
          </v-btn>
        </template>
        <v-list density="compact">
          <v-list-subheader>选择语音方言</v-list-subheader>
          <v-list-item @click="selectedDialect='mandarin'" value="mandarin">
            <template v-slot:prepend><v-icon :color="selectedDialect==='mandarin'?'primary':''">mdi-check</v-icon></template>
            普通话
          </v-list-item>
          <v-list-item @click="selectedDialect='sichuan'" value="sichuan">
            <template v-slot:prepend><v-icon :color="selectedDialect==='sichuan'?'primary':''">mdi-check</v-icon></template>
            四川话
          </v-list-item>
          <v-list-item @click="selectedDialect='cantonese'" value="cantonese">
            <template v-slot:prepend><v-icon :color="selectedDialect==='cantonese'?'primary':''">mdi-check</v-icon></template>
            粤语
          </v-list-item>
        </v-list>
      </v-menu>

      <v-btn
        :disabled="!message.trim() && !previewUrl"
        :loading="loading"
        icon="mdi-send"
        color="primary"
        variant="flat"
        class="mb-1 ml-1"
        @click="sendMessage"
      ></v-btn>
    </v-card>
  </v-sheet>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ loading: boolean }>()
const emit = defineEmits(['send'])

const message = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref<string | null>(null)
const selectedDialect = ref('mandarin')
const isRecording = ref(false) // 暂未实现真实录音逻辑，仅UI占位

// 处理文件
const triggerFileInput = () => fileInput.value?.click()
const handleFileChange = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  
  // 这里应该调用 API 上传图片换取 URL，为了简化先用 POST /upload/
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    const res = await fetch('http://localhost:8000/upload/', { method: 'POST', body: formData })
    const data = await res.json()
    previewUrl.value = data.url // 拿到后端返回的 URL
  } catch (e) {
    console.error('Upload failed', e)
  }
}

const clearFile = () => {
  previewUrl.value = null
  if (fileInput.value) fileInput.value.value = ''
}

const sendMessage = () => {
  if (!message.value.trim() && !previewUrl.value) return
  
  if (previewUrl.value) {
    emit('send', message.value, 'image', previewUrl.value)
    clearFile()
  } else {
    emit('send', message.value, 'text', null, selectedDialect.value)
  }
  message.value = ''
}
</script>

<style scoped>
.custom-textarea :deep(textarea) {
  padding-top: 10px !important;
  max-height: 150px;
}
.animate-pulse {
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
</style>