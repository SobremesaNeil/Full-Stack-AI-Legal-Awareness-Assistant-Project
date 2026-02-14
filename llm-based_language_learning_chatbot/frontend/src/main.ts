import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import '@mdi/font/css/materialdesignicons.min.css'

import App from './App.vue'
import router from './router'

const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          background: '#F8F9FA',
          primary: '#1867C0',
          secondary: '#5CBBF6',
          surface: '#FFFFFF',
          'surface-variant': '#F2F2F2',
          'on-surface': '#000000',
          'on-primary': '#FFFFFF',
        },
      },
      dark: {
        colors: {
          background: '#121212',
          primary: '#1867C0',
          secondary: '#5CBBF6',
          surface: '#1E1E1E',
          'surface-variant': '#2D2D2D',
          'on-surface': '#FFFFFF',
          'on-primary': '#FFFFFF',
        },
      },
    },
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)

app.mount('#app')
