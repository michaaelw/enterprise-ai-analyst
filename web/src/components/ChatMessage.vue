<script setup lang="ts">
import type { ChatEntry } from '@/types'
import SourceCard from './SourceCard.vue'

defineProps<{ entry: ChatEntry }>()
</script>

<template>
  <div
    class="flex"
    :class="entry.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <div
      class="max-w-[75%] rounded-lg px-4 py-3 shadow-sm"
      :class="entry.role === 'user'
        ? 'bg-blue-600 text-white'
        : 'bg-white text-gray-800 border'"
    >
      <p class="whitespace-pre-wrap">{{ entry.content }}</p>

      <template v-if="entry.role === 'assistant'">
        <!-- Metadata -->
        <div v-if="entry.latencyMs || entry.strategy" class="mt-2 flex gap-3 text-xs text-gray-400">
          <span v-if="entry.latencyMs">{{ entry.latencyMs.toFixed(0) }}ms</span>
          <span v-if="entry.strategy">{{ entry.strategy }}</span>
        </div>

        <!-- Sources -->
        <div v-if="entry.sources?.length" class="mt-3 space-y-1.5">
          <div class="text-xs font-medium text-gray-500">Sources</div>
          <SourceCard v-for="s in entry.sources" :key="s.chunk.id" :source="s" />
        </div>
      </template>
    </div>
  </div>
</template>
