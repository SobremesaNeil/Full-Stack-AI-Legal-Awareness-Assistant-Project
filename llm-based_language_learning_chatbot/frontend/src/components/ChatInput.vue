<template>
  <div class="input-container">
    <div class="toolbar">
      <label class="tool-btn">
        📷
        <input type="file" accept="image/*" @change="handleImageUpload" hidden />
      </label>
      
      <select v-model="selectedDialect" class="dialect-select">
        <option value="mandarin">普通话</option>
        <option value="cantonese">粤语</option>
        <option value="sichuan">四川话</option>
      </select>
    </div>

    <v-textarea
      v-model="message"
      :placeholder="isUploading ? '正在上传图片...' : '输入法律问题，支持描述图片...'"
      auto-grow
      rows="1"
      max-rows="5"
      variant="outlined"
      hide-details
      @keydown.enter.prevent="sendMessage"
      :disabled="isLoading || isUploading"
    >
      <template v-slot:append-inner>
        <v-btn
          icon="mdi-send"
          variant="text"
          color="primary"
          @click="sendMessage"
          :loading="isLoading"
          :disabled="!message.trim() && !pendingImage"
        ></v-btn>
      </template>
    </v-textarea>
    
    <div v-if="pendingImage" class="preview-chip">
      图片已就绪 ({{ pendingImage.name }}) 
      <span @click="pendingImage = null" style="cursor:pointer; color:red">✕</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useChatStore } from '@/stores/counter'; // 假设用了Pinia，或者直接emit

const props = defineProps<{
  isLoading: boolean;
}>();

const emit = defineEmits<{
  (e: 'send', text: string, type: string, url?: string, dialect?: string): void;
}>();

const message = ref('');
const selectedDialect = ref('mandarin');
const isUploading = ref(false);
const pendingImage = ref<{file: File, url: string, name: string} | null>(null);

// 处理图片上传到服务器
const handleImageUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;

  isUploading.value = true;
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('http://localhost:8000/upload/', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    pendingImage.value = {
      file: file,
      url: data.url,
      name: file.name
    };
  } catch (error) {
    alert('图片上传失败');
  } finally {
    isUploading.value = false;
  }
};

const sendMessage = () => {
  if ((!message.value.trim() && !pendingImage.value) || props.isLoading) return;

  // 1. 如果有图片，发送图片类型消息
  if (pendingImage.value) {
    emit('send', message.value, 'image', pendingImage.value.url, selectedDialect.value);
    pendingImage.value = null;
  } else {
    // 2. 否则发送纯文本
    emit('send', message.value, 'text', undefined, selectedDialect.value);
  }
  
  message.value = '';
};
</script>

<style scoped>
.input-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #fff;
  padding: 10px;
  border-top: 1px solid #eee;
}
.toolbar {
  display: flex;
  gap: 15px;
  align-items: center;
  padding-left: 5px;
}
.tool-btn {
  cursor: pointer;
  font-size: 1.2rem;
  transition: transform 0.2s;
}
.tool-btn:hover {
  transform: scale(1.1);
}
.dialect-select {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 2px 5px;
  font-size: 0.8rem;
}
.preview-chip {
  font-size: 0.8rem;
  color: #666;
  background: #f0f0f0;
  padding: 4px 8px;
  border-radius: 4px;
  width: fit-content;
}
</style>