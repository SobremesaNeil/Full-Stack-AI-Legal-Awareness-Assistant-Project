<<script setup lang="ts">
import ChatWindow from '@/components/ChatWindow.vue'
</script>

<template>
  <div class="home-container">
    <ChatWindow />
  </div>
</template>

<style scoped>
.home-container {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
}
</style>