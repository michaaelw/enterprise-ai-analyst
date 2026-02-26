<script setup lang="ts">
import { ref } from 'vue'
import type { RetrievalResultData } from '@/types'

defineProps<{ source: RetrievalResultData }>()

const expanded = ref(false)
</script>

<template>
  <div class="border rounded-lg bg-gray-50 text-sm">
    <button
      class="flex items-center justify-between w-full px-3 py-2 text-left hover:bg-gray-100 transition-colors"
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
      <span class="shrink-0 ml-2 text-xs text-gray-500">
        {{ (source.score * 100).toFixed(1) }}%
      </span>
    </button>
    <div v-if="expanded" class="px-3 pb-3 text-gray-700 whitespace-pre-wrap border-t">
      {{ source.chunk.content }}
    </div>
  </div>
</template>
