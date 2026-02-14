<template>
  <v-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    max-width="500px"
  >
    <v-card>
      <v-card-title>{{ title }}</v-card-title>
      <v-card-text>{{ text }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          color="primary"
          variant="text"
          @click="$emit('update:modelValue', false); $emit('cancel')"
        >
          {{ cancelText || '取消' }}
        </v-btn>
        <v-btn
          :color="confirmColor"
          variant="text"
          @click="$emit('update:modelValue', false); $emit('confirm')"
        >
          {{ confirmText || '确定' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: boolean
  title: string
  text: string
  confirmText?: string
  cancelText?: string
  type?: 'info' | 'warning' | 'error'
}>()

defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const confirmColor = computed(() => {
  switch (props.type) {
    case 'error':
      return 'error'
    case 'warning':
      return 'warning'
    default:
      return 'primary'
  }
})
</script>

<style scoped>
:deep(.v-btn) {
  text-transform: none;
}
</style> 