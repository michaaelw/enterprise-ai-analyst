<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import HealthBadge from './HealthBadge.vue'

const sidebarOpen = ref(true)
</script>

<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <aside
      :class="sidebarOpen ? 'w-56' : 'w-0 -ml-56'"
      class="flex flex-col bg-gray-900 text-white transition-all duration-200 shrink-0"
    >
      <div class="p-4 text-lg font-semibold border-b border-gray-700">
        AI Analyst
      </div>
      <nav class="flex-1 p-2 space-y-1">
        <RouterLink
          to="/"
          class="block px-3 py-2 rounded hover:bg-gray-700 transition-colors"
          active-class="bg-gray-700"
        >
          Chat
        </RouterLink>
        <RouterLink
          to="/ingest"
          class="block px-3 py-2 rounded hover:bg-gray-700 transition-colors"
          active-class="bg-gray-700"
        >
          Ingest
        </RouterLink>
      </nav>
      <div class="p-3 border-t border-gray-700">
        <HealthBadge />
      </div>
    </aside>

    <!-- Main content -->
    <div class="flex flex-col flex-1 min-w-0">
      <header class="flex items-center h-12 px-4 border-b bg-white shrink-0">
        <button
          class="mr-3 text-gray-500 hover:text-gray-800"
          @click="sidebarOpen = !sidebarOpen"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <span class="font-medium text-sm text-gray-600">Enterprise AI Analyst</span>
      </header>
      <main class="flex-1 overflow-auto">
        <slot />
      </main>
    </div>
  </div>
</template>
