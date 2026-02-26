<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'

const content = ref('')
const source = ref('')
const isLoading = ref(false)
const result = ref<{ document_id: string; chunks_created: number } | null>(null)
const error = ref('')

async function submit() {
  if (!content.value.trim() || isLoading.value) return

  isLoading.value = true
  error.value = ''
  result.value = null

  try {
    result.value = await api.ingest({
      content: content.value,
      source: source.value || undefined,
    })
    content.value = ''
    source.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Ingestion failed'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto p-6">
    <h1 class="text-xl font-semibold mb-4">Ingest Document</h1>

    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Source Name</label>
        <input
          v-model="source"
          type="text"
          placeholder="e.g., meeting_notes, product_docs"
          class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Content</label>
        <textarea
          v-model="content"
          placeholder="Paste document content here..."
          rows="12"
          class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
        />
      </div>

      <button
        :disabled="isLoading || !content.trim()"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        @click="submit"
      >
        {{ isLoading ? 'Ingesting...' : 'Ingest' }}
      </button>

      <!-- Result -->
      <div v-if="result" class="p-4 bg-green-50 border border-green-200 rounded-lg">
        <p class="text-sm text-green-800">
          Document ingested successfully.
        </p>
        <p class="text-xs text-green-600 mt-1">
          ID: {{ result.document_id }} &middot; {{ result.chunks_created }} chunks created
        </p>
      </div>

      <!-- Error -->
      <div v-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-sm text-red-800">{{ error }}</p>
      </div>
    </div>
  </div>
</template>
