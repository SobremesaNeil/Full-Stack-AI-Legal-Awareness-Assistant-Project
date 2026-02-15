<template>
  <div :class="['message-wrapper', message.role]">
    <div class="avatar">
      {{ message.role === 'user' ? '👤' : '⚖️' }}
    </div>
    
    <div class="content-box">
      <div v-if="message.type === 'image'" class="media-content">
        <img :src="message.mediaUrl" alt="上传图片" class="chat-image" />
        <p v-if="message.content">{{ message.content }}</p>
      </div>

      <div v-else-if="message.type === 'mindmap'" class="mindmap-content">
        <div class="mindmap-label">🧠 法律逻辑导图</div>
        <svg ref="svgRef" class="mindmap-svg"></svg>
      </div>

      <div v-else class="text-content" v-html="renderMarkdown(message.content)"></div>

      <div v-if="message.role === 'assistant' && !message.audioUrl" class="audio-controls">
         </div>
      <div v-if="message.mediaUrl && message.type === 'audio'" class="audio-player">
         <audio controls :src="message.mediaUrl"></audio>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { Transformer } from 'markmap-lib';
import { Markmap } from 'markmap-view';
import { marked } from 'marked';
import type { Message } from '@/types/chat';

const props = defineProps<{
  message: Message;
}>();

const svgRef = ref<SVGElement | null>(null);

// Markdown 渲染
const renderMarkdown = (text: string) => {
  return marked(text);
};

// 渲染思维导图
const renderMindmap = () => {
  if (props.message.type === 'mindmap' && svgRef.value) {
    // 清空旧内容
    svgRef.value.innerHTML = '';
    const transformer = new Transformer();
    const { root } = transformer.transform(props.message.content);
    Markmap.create(svgRef.value, {
        scrollForPan: true,
        zoom: true,
    }, root);
  }
};

onMounted(() => {
  if (props.message.type === 'mindmap') {
    setTimeout(renderMindmap, 100); // 稍微延迟确保DOM渲染
  }
});

watch(() => props.message, () => {
    renderMindmap();
}, { deep: true });
</script>

<style scoped>
.message-wrapper {
  display: flex;
  margin-bottom: 20px;
  gap: 10px;
}
.message-wrapper.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 40px;
  height: 40px;
  background: #eee;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}
.content-box {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #f4f4f4;
  color: #333;
  line-height: 1.6;
}
.user .content-box {
  background: #1976D2;
  color: white;
}
.chat-image {
  max-width: 100%;
  border-radius: 8px;
  margin-bottom: 5px;
}
.mindmap-content {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 10px;
  width: 500px;
  height: 300px;
  overflow: hidden;
}
.mindmap-svg {
  width: 100%;
  height: 100%;
}
.mindmap-label {
  font-size: 0.8rem;
  font-weight: bold;
  color: #1976D2;
  margin-bottom: 5px;
}
</style>