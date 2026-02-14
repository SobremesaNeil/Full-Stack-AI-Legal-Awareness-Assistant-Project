<script setup lang="ts">
import ChatWindow from './components/ChatWindow.vue'
</script>

<template>
  <v-app>
    <v-main>
      <div class="app-container">
        <chat-window />
      </div>
    </v-main>
  </v-app>
</template>

<style>
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  background-color: rgb(var(--v-theme-background));
}

.app-container {
  max-width: 1200px;
  min-height: 100vh;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.v-application {
  background-color: rgb(var(--v-theme-background)) !important;
}

.v-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
