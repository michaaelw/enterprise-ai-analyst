<script setup lang="ts">
import { ref } from 'vue'
import type { RetrievalResultData } from '@/types'

defineProps<{ source: RetrievalResultData }>()

const expanded = ref(false)
</script>

<template>
  <div class="border border-gray-200 rounded-xl bg-white shadow-sm text-sm">
    <button
      class="flex items-center justify-between w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors"
      @click="expanded = !expanded"
    >
      <div class="flex items-center gap-2 min-w-0">
        <span
          class="shrink-0 px-1.5 py-0.5 text-xs font-medium rounded"
          :class="source.source === 'vector' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'"
        >
          {{ source.source }}
        </span>
        <span class="truncate text-gray-600">
          {{ source.chunk.document_id.slice(0, 8) }}
        </span>
      </div>
      <div class="shrink-0 ml-2 flex items-center gap-1.5">
        <span class="text-xs text-gray-500">
          {{ (source.score * 100).toFixed(1) }}%
        </span>
        <svg
          class="w-3.5 h-3.5 text-gray-400 transition-transform duration-200"
          :class="expanded ? 'rotate-180' : ''"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clip-rule="evenodd"
          />
        </svg>
      </div>
    </button>
    <div v-if="expanded" class="px-3 pb-3 text-gray-700 whitespace-pre-wrap border-t border-gray-100 text-xs leading-relaxed pt-2">
      {{ source.chunk.content }}
    </div>
  </div>
</template>
