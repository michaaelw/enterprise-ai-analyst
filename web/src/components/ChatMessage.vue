<script setup lang="ts">
import { computed } from 'vue'
import type { ChatEntry } from '@/types'
import SourceCard from './SourceCard.vue'

const props = defineProps<{ entry: ChatEntry }>()

const timeLabel = computed(() => {
  const d = props.entry.timestamp
  if (!d) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
})

const streaming = computed(() => props.entry.role === 'assistant' && !props.entry.latencyMs && props.entry.content !== '')
</script>

<template>
  <div
    class="flex items-end gap-2 group"
    :class="entry.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
  >
    <!-- Avatar -->
    <div class="shrink-0 mb-1">
      <!-- User avatar -->
      <div
        v-if="entry.role === 'user'"
        class="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center"
      >
        <svg class="w-4 h-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
        </svg>
      </div>
      <!-- Assistant avatar -->
      <div
        v-else
        class="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center"
      >
        <svg class="w-4 h-4 text-white" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.381c-.833.067-1.171 1.107-.536 1.651l3.62 3.102-1.106 4.637c-.194.813.691 1.456 1.405 1.02L10 15.591l4.069 2.485c.713.436 1.598-.207 1.404-1.02l-1.106-4.637 3.62-3.102c.635-.544.297-1.584-.536-1.65l-4.752-.382-1.83-4.401z"
            clip-rule="evenodd"
          />
        </svg>
      </div>
    </div>

    <!-- Bubble + timestamp -->
    <div
      class="flex flex-col gap-1"
      :class="entry.role === 'user' ? 'items-end' : 'items-start'"
    >
      <!-- Agent status indicator -->
      <div v-if="entry.agentStatus" class="flex items-center gap-2 px-3 py-1.5 text-xs text-blue-600">
        <svg class="w-3 h-3 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <span>{{ entry.agentStatus.message }}</span>
      </div>

      <div
        class="max-w-[75%] px-4 py-3 shadow-sm"
        :class="entry.role === 'user'
          ? 'bg-blue-600 text-white rounded-2xl rounded-br-sm'
          : 'bg-white text-gray-800 rounded-2xl rounded-bl-sm'"
      >
        <p class="whitespace-pre-wrap">{{ entry.content }}<span v-if="streaming" class="typing-cursor">|</span></p>

        <template v-if="entry.role === 'assistant'">
          <!-- Metadata pills -->
          <div v-if="entry.latencyMs || entry.strategy" class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-if="entry.latencyMs"
              class="bg-gray-100 text-gray-500 rounded-md px-2 py-0.5 text-xs"
            >
              {{ entry.latencyMs.toFixed(0) }}ms
            </span>
            <span
              v-if="entry.strategy"
              class="bg-gray-100 text-gray-500 rounded-md px-2 py-0.5 text-xs"
            >
              {{ entry.strategy }}
            </span>
          </div>

          <!-- Sources -->
          <div v-if="entry.sources?.length" class="mt-3 space-y-1.5">
            <div class="flex items-center gap-1 text-xs font-medium text-gray-500">
              <svg class="w-3.5 h-3.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd" />
              </svg>
              {{ entry.sources.length }} {{ entry.sources.length === 1 ? 'source' : 'sources' }}
            </div>
            <SourceCard v-for="s in entry.sources" :key="s.chunk.id" :source="s" />
          </div>
        </template>
      </div>

      <!-- Timestamp (visible on group hover) -->
      <span class="text-xs text-gray-400 px-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
        {{ timeLabel }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.typing-cursor {
  animation: blink 0.7s step-end infinite;
  color: inherit;
  font-weight: 300;
}
@keyframes blink {
  50% { opacity: 0; }
}
</style>
