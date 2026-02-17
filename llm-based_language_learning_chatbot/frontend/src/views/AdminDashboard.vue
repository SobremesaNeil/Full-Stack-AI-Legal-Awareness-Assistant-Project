<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4 font-weight-bold text-primary">
        <v-icon icon="mdi-shield-account" size="large" class="mr-2" />
        专家控制台
      </h1>
      <v-spacer />
      <v-chip color="info" variant="flat">
        <v-icon start icon="mdi-clock-outline"></v-icon>
        {{ new Date().toLocaleDateString() }}
      </v-chip>
    </div>

    <v-card elevation="2" class="rounded-lg">
      <v-tabs v-model="activeTab" color="primary" bg-color="grey-lighten-4">
        <v-tab value="tickets" prepend-icon="mdi-ticket-account">咨询工单处理</v-tab>
        <v-tab value="rules" prepend-icon="mdi-robot-confused">高频规则库 (AI拦截)</v-tab>
      </v-tabs>

      <v-card-text>
        <v-window v-model="activeTab">
          
          <v-window-item value="tickets">
            <div v-if="loading" class="d-flex justify-center pa-10">
              <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
            </div>
            
            <div v-else-if="tickets.length === 0" class="text-center pa-10 text-grey">
              <v-icon icon="mdi-checkbox-marked-circle-outline" size="64" class="mb-2" />
              <p>太棒了！当前没有待处理的工单。</p>
            </div>

            <v-row v-else>
              <v-col v-for="ticket in tickets" :key="ticket.id" cols="12">
                <v-card border flat class="mb-2">
                  <v-card-item>
                    <template v-slot:prepend>
                      <v-avatar color="primary" variant="tonal">
                        {{ ticket.user_id }}
                      </v-avatar>
                    </template>
                    <v-card-title>{{ ticket.title }}</v-card-title>
                    <v-card-subtitle>
                      提交时间: {{ new Date(ticket.created_at).toLocaleString() }}
                    </v-card-subtitle>
                    <template v-slot:append>
                      <v-chip :color="getStatusColor(ticket.status)" size="small" label>
                        {{ ticket.status === 'pending' ? '待处理' : '已回复' }}
                      </v-chip>
                    </template>
                  </v-card-item>

                  <v-card-text class="py-3 text-body-1">
                    {{ ticket.description }}
                  </v-card-text>

                  <v-divider></v-divider>

                  <div class="pa-4 bg-grey-lighten-5">
                    <div v-if="ticket.expert_reply">
                      <div class="text-subtitle-2 text-primary mb-1">👨‍⚖️ 您的法律意见：</div>
                      <div class="text-body-2">{{ ticket.expert_reply }}</div>
                    </div>
                    <div v-else>
                      <v-textarea
                        v-model="replyText[ticket.id]"
                        label="撰写法律意见..."
                        variant="outlined"
                        rows="3"
                        auto-grow
                        bg-color="white"
                        hide-details
                        class="mb-3"
                      ></v-textarea>
                      <div class="d-flex justify-end">
                        <v-btn 
                          color="primary" 
                          prepend-icon="mdi-send"
                          @click="handleReply(ticket.id)"
                          :loading="submitting === ticket.id"
                        >
                          提交回复
                        </v-btn>
                      </div>
                    </div>
                  </div>
                </v-card>
              </v-col>
            </v-row>
          </v-window-item>

          <v-window-item value="rules">
            <div class="d-flex justify-space-between align-center mb-4">
              <v-alert
                icon="mdi-information"
                color="info"
                variant="tonal"
                density="compact"
                class="flex-grow-1 mr-4"
              >
                此处配置的规则将优先于 AI 模型生效。当用户问题命中关键词时，系统将直接返回标准答案。
              </v-alert>
              <v-btn color="success" prepend-icon="mdi-plus" @click="openRuleDialog">
                添加新规则
              </v-btn>
            </div>

            <v-data-table
              :headers="ruleHeaders"
              :items="rules"
              :loading="loadingRules"
              class="elevation-1 rounded-lg"
            >
              <template v-slot:item.patterns="{ item }">
                <v-chip-group>
                  <v-chip 
                    v-for="(pat, idx) in item.patterns" 
                    :key="idx" 
                    size="small" 
                    color="indigo-lighten-4" 
                    variant="flat"
                  >
                    {{ pat }}
                  </v-chip>
                </v-chip-group>
              </template>
              
              <template v-slot:item.source="{ item }">
                <v-chip size="x-small" color="grey" variant="outlined">{{ item.source }}</v-chip>
              </template>

              <template v-slot:item.actions="{ item }">
                <v-btn 
                  icon="mdi-delete" 
                  size="small" 
                  color="error" 
                  variant="text" 
                  @click="handleDeleteRule(item.id)"
                ></v-btn>
              </template>
            </v-data-table>
          </v-window-item>

        </v-window>
      </v-card-text>
    </v-card>

    <v-dialog v-model="dialog" max-width="600px">
      <v-card>
        <v-card-title class="bg-primary text-white pa-4">
          添加高频拦截规则
        </v-card-title>
        <v-card-text class="pt-6">
          <v-form v-model="valid" @submit.prevent="submitRule">
            <v-text-field
              v-model="newRule.patternsStr"
              label="触发关键词/正则 (Keywords)"
              hint="多个关键词请用中文逗号或英文逗号分隔，例如：客服电话, 联系人工"
              persistent-hint
              variant="outlined"
              class="mb-2"
              :rules="[v => !!v || '请输入至少一个关键词']"
            ></v-text-field>
            
            <v-textarea
              v-model="newRule.answer"
              label="标准回复内容 (Standard Answer)"
              variant="outlined"
              rows="3"
              :rules="[v => !!v || '请输入标准回复']"
            ></v-textarea>
            
            <v-text-field
              v-model="newRule.source"
              label="法律依据/来源 (Source)"
              placeholder="例如：《民法典》第XX条 或 平台规定"
              variant="outlined"
              :rules="[v => !!v || '请输入来源']"
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" @click="submitRule" :disabled="!valid">保存并生效</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" location="top">
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { getAdminTickets, replyTicket, getRules, createRule, deleteRule } from '@/services/api'

// --- 类型定义 ---
interface Ticket {
  id: number
  user_id: number
  title: string
  description: string
  status: 'pending' | 'answered'
  created_at: string
  expert_reply?: string
}

interface Rule {
  id: number
  patterns: string[]
  answer: string
  source: string
}

// --- 状态管理 ---
const activeTab = ref('tickets')
const tickets = ref<Ticket[]>([])
const rules = ref<Rule[]>([])
const loading = ref(true)
const loadingRules = ref(false)
const submitting = ref<number | null>(null)
const replyText = ref<Record<number, string>>({})

// 规则表单状态
const dialog = ref(false)
const valid = ref(false)
const newRule = reactive({
  patternsStr: '',
  answer: '',
  source: '',
  active: true
})

// 提示条状态
const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})

// 表格表头
const ruleHeaders = [
  { title: 'ID', key: 'id', width: '80px' },
  { title: '触发关键词 (Regex)', key: 'patterns', sortable: false },
  { title: '标准回复', key: 'answer' },
  { title: '来源', key: 'source', width: '150px' },
  { title: '操作', key: 'actions', align: 'end' as const, sortable: false },
]

// --- 初始化 ---
onMounted(async () => {
  await loadTickets()
  await loadRules()
})

// --- 逻辑: 工单 ---
async function loadTickets() {
  loading.value = true
  try {
    tickets.value = await getAdminTickets()
  } catch (e) {
    showMsg('加载工单失败，请检查管理员权限', 'error')
  } finally {
    loading.value = false
  }
}

async function handleReply(id: number) {
  const text = replyText.value[id]
  if (!text) return showMsg('请输入回复内容', 'warning')
  
  submitting.value = id
  try {
    await replyTicket(id, text)
    showMsg('回复已提交')
    await loadTickets()
    replyText.value[id] = ''
  } catch(e) {
    showMsg('提交失败', 'error')
  } finally {
    submitting.value = null
  }
}

// --- 逻辑: 规则库 ---
async function loadRules() {
  loadingRules.value = true
  try {
    rules.value = await getRules()
  } catch (e) {
    console.error('Failed to load rules')
  } finally {
    loadingRules.value = false
  }
}

function openRuleDialog() {
  newRule.patternsStr = ''
  newRule.answer = ''
  newRule.source = ''
  dialog.value = true
}

async function submitRule() {
  if (!newRule.patternsStr || !newRule.answer) return

  // 核心逻辑：将逗号分隔的字符串转为数组，并去空格
  const patternsArray = newRule.patternsStr
    .split(/[,，]/) // 支持中文逗号和英文逗号
    .map(s => s.trim())
    .filter(s => s.length > 0)

  if (patternsArray.length === 0) {
    showMsg('请输入有效的关键词', 'warning')
    return
  }

  try {
    await createRule({
      patterns: patternsArray,
      answer: newRule.answer,
      source: newRule.source,
      active: true
    })
    showMsg('新规则已添加并生效！')
    dialog.value = false
    await loadRules() // 刷新列表
  } catch (e) {
    showMsg('添加规则失败', 'error')
  }
}

async function handleDeleteRule(id: number) {
  if (!confirm('确定要删除这条规则吗？')) return
  try {
    await deleteRule(id)
    showMsg('规则已删除')
    await loadRules()
  } catch (e) {
    showMsg('删除失败', 'error')
  }
}

// --- 辅助函数 ---
function getStatusColor(status: string) {
  return status === 'pending' ? 'warning' : 'success'
}

function showMsg(text: string, color: 'success' | 'error' | 'warning' = 'success') {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}
</script>

<style scoped>
/* Vuetify 处理了大部分样式，这里只需微调 */
.v-card-text {
  line-height: 1.6;
}
</style>