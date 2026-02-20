<template>
  <div :class="['message', message.role]">
    <div class="avatar">
      {{ message.role === 'user' ? '👤' : '⚖️' }}
    </div>
    <div class="content-wrapper">
      <div class="bubble" v-html="parsedContent"></div>
      
      <div v-if="mindmapData" class="mindmap-container mt-2">
        <div class="mindmap-header">
          <v-icon size="small" class="mr-1">mdi-sitemap</v-icon> 案情脉络图
        </div>
        <svg ref="mindmapSvg" class="mindmap-svg"></svg>
      </div>

      <div v-if="documentData" class="document-container mt-2">
        <div class="document-header d-flex justify-space-between align-center">
          <div><v-icon size="small" class="mr-1">mdi-file-document-outline</v-icon> {{ documentTitle }}</div>
          <v-btn size="x-small" color="primary" variant="flat" @click="downloadDocument">
            <v-icon size="small" class="mr-1">mdi-download</v-icon> 下载文书
          </v-btn>
        </div>
        <div class="document-body custom-scrollbar" v-html="parsedDocument"></div>
      </div>
      
      <img v-if="message.media_url" :src="message.media_url" class="media-img" />

      <div v-if="message.citations" class="citations mt-2">
        <h4>📚 法律依据:</h4>
        <div class="citation-text">{{ message.citations }}</div>
      </div>

      <div v-if="message.role === 'assistant'" class="feedback-actions">
        <button @click="sendFeedback(1)" :class="{ active: feedbackStatus === 1 }" title="回答准确">👍</button>
        <button @click="sendFeedback(-1)" :class="{ active: feedbackStatus === -1 }" title="回答有误">👎</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, nextTick, watch } from 'vue'
import { marked } from 'marked'
import { submitFeedback } from '@/services/api'
import type { Message } from '@/types/chat'
// 引入 mindmap
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'

const props = defineProps<{ message: Message }>()
const feedbackStatus = ref(0)
const mindmapSvg = ref<SVGElement | null>(null)

// --- 数据解析提取 ---
const extractTagContent = (text: string, tag: string) => {
  const regex = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, 'i')
  const match = text.match(regex)
  return match ? match[1].trim() : null
}

const extractTagAttribute = (text: string, tag: string, attr: string) => {
  const regex = new RegExp(`<${tag}[^>]*${attr}="([^"]*)"[^>]*>`, 'i')
  const match = text.match(regex)
  return match ? match[1] : '法律文书'
}

// 提取思维导图 Markdown
const mindmapData = computed(() => extractTagContent(props.message.content || '', 'mindmap'))

// 提取文书内容与标题
const documentData = computed(() => extractTagContent(props.message.content || '', 'document'))
const documentTitle = computed(() => extractTagAttribute(props.message.content || '', 'document', 'title'))
const parsedDocument = computed(() => documentData.value ? marked(documentData.value) : '')

// 过滤掉自定义标签，仅显示纯文本对话
const parsedContent = computed(() => {
  let content = props.message.content || ''
  content = content.replace(/<mindmap>[\s\S]*?<\/mindmap>/gi, '')
  content = content.replace(/<document[^>]*>[\s\S]*?<\/document>/gi, '')
  return marked(content)
})

// --- 思维导图渲染 ---
const transformer = new Transformer()
const renderMindmap = async () => {
  if (mindmapData.value && mindmapSvg.value) {
    await nextTick()
    const { root } = transformer.transform(mindmapData.value)
    mindmapSvg.value.innerHTML = '' // 清除旧图形
    Markmap.create(mindmapSvg.value, {
      autoFit: true,
      color: () => '#1976D2', // 法律蓝
      style: id => `${id} * { font-family: inherit; }`
    }, root)
  }
}

watch(mindmapData, renderMindmap)
onMounted(renderMindmap)

// --- 文书下载 ---
const downloadDocument = () => {
  if (!documentData.value) return
  const blob = new Blob([documentData.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${documentTitle.value}.md`
  a.click()
  URL.revokeObjectURL(url)
}

async function sendFeedback(score: number) {
  if (feedbackStatus.value === score) return
  try {
    if (props.message.messageId) {
       await submitFeedback(props.message.messageId, score)
       feedbackStatus.value = score
       alert(score === 1 ? '感谢您的好评！' : '感谢反馈，专家稍后会进行纠偏。')
    }
  } catch (e) {
    console.error(e)
  }
}
</script>

<style scoped>
.message { display: flex; margin-bottom: 1.5rem; gap: 10px; }
.message.user { flex-direction: row-reverse; }
.avatar { font-size: 1.5rem; width: 40px; height: 40px; background: #eee; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;}
.content-wrapper { max-width: 85%; display: flex; flex-direction: column; gap: 5px; overflow-x: hidden; }
.bubble { padding: 12px 16px; border-radius: 12px; line-height: 1.6; word-wrap: break-word; }
.user .bubble { background: #007bff; color: white; border-bottom-right-radius: 2px; }
.assistant .bubble { background: #f8f9fa; color: #333; border: 1px solid #e9ecef; border-bottom-left-radius: 2px; }
.media-img { max-width: 200px; border-radius: 8px; margin-top: 5px; }

/* 引用样式 */
.citations { font-size: 0.85rem; background: #fffbe6; border: 1px solid #ffe58f; padding: 10px; border-radius: 6px; color: #555; }
.citations h4 { margin: 0 0 6px 0; color: #d48806; font-size: 0.9rem; }
.citation-text { white-space: pre-wrap; line-height: 1.5; }

/* 思维导图区块 */
.mindmap-container { border: 1px solid #e0e0e0; border-radius: 8px; background: #fff; overflow: hidden; }
.mindmap-header { background: #f5f5f5; padding: 6px 12px; font-size: 0.85rem; font-weight: bold; color: #555; border-bottom: 1px solid #e0e0e0; }
.mindmap-svg { width: 100%; height: 250px; background: #fafafa; }

/* 法律文书区块 */
.document-container { border: 1px solid #bbdefb; border-radius: 8px; background: #fff; overflow: hidden; }
.document-header { background: #e3f2fd; padding: 8px 12px; font-weight: bold; color: #1565c0; border-bottom: 1px solid #bbdefb; }
.document-body { padding: 16px; font-family: 'Courier New', Courier, monospace; font-size: 0.9rem; background: #fcfcfc; max-height: 300px; overflow-y: auto; line-height: 1.6; }

/* 反馈按钮 */
.feedback-actions { display: flex; gap: 12px; margin-top: 4px; padding-left: 4px; }
.feedback-actions button { background: none; border: none; cursor: pointer; opacity: 0.4; transition: all 0.2s; font-size: 1.1rem; }
.feedback-actions button:hover { opacity: 1; transform: scale(1.1); }
.feedback-actions button.active { opacity: 1; transform: scale(1.2); filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)); }

/* 滚动条美化 */
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #ccc; border-radius: 3px; }
</style>