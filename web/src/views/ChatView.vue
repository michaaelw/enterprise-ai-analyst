<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { api } from '@/api/client'
import type { ChatEntry } from '@/types'
import ChatMessage from '@/components/ChatMessage.vue'

const messages = ref<ChatEntry[]>([])
const inputQuery = ref('')
const isLoading = ref(false)
const strategy = ref<'hybrid' | 'vector_only'>('hybrid')
const topK = ref(10)
const chatContainer = ref<HTMLElement | null>(null)

const suggestions = [
  'What are the key company policies?',
  'Summarize the latest financial report',
  'What was discussed in the last meeting?',
]

function makeId() {
  return crypto.randomUUID()
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function submit() {
  const query = inputQuery.value.trim()
  if (!query || isLoading.value) return

  const userEntry: ChatEntry = {
    id: makeId(),
    role: 'user',
    content: query,
    timestamp: new Date(),
  }
  messages.value.push(userEntry)
  inputQuery.value = ''
  isLoading.value = true
  await scrollToBottom()

  try {
    const res = await api.query({ query, strategy: strategy.value, top_k: topK.value })
    const assistantEntry: ChatEntry = {
      id: makeId(),
      role: 'assistant',
      content: res.answer,
      sources: res.sources,
      latencyMs: res.latency_ms,
      strategy: res.strategy,
      timestamp: new Date(),
    }
    messages.value.push(assistantEntry)
  } catch (err) {
    const errorEntry: ChatEntry = {
      id: makeId(),
      role: 'assistant',
      content: `Error: ${err instanceof Error ? err.message : 'Request failed'}`,
      timestamp: new Date(),
    }
    messages.value.push(errorEntry)
  } finally {
    isLoading.value = false
    await scrollToBottom()
  }
}

function useSuggestion(s: string) {
  inputQuery.value = s
  submit()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Messages -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- Empty state -->
      <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full text-gray-400">
        <p class="text-lg mb-4">Ask a question about your documents</p>
        <div class="flex flex-wrap gap-2 justify-center">
          <button
            v-for="s in suggestions"
            :key="s"
            class="px-3 py-1.5 text-sm border rounded-full hover:bg-gray-100 transition-colors text-gray-600"
            @click="useSuggestion(s)"
          >
            {{ s }}
          </button>
        </div>
      </div>

      <ChatMessage v-for="m in messages" :key="m.id" :entry="m" />

      <!-- Loading indicator -->
      <div v-if="isLoading" class="flex justify-start">
        <div class="bg-white border rounded-lg px-4 py-3 shadow-sm text-gray-400">
          Thinking...
        </div>
      </div>
    </div>

    <!-- Input bar -->
    <div class="border-t bg-white p-4">
      <div class="flex items-center gap-2 mb-2">
        <select
          v-model="strategy"
          class="text-xs border rounded px-2 py-1 text-gray-600 bg-gray-50"
        >
          <option value="hybrid">Hybrid</option>
          <option value="vector_only">Vector Only</option>
        </select>
        <label class="text-xs text-gray-500">
          Top K:
          <input
            v-model.number="topK"
            type="number"
            min="1"
            max="50"
            class="w-14 ml-1 border rounded px-1.5 py-0.5 text-xs"
          />
        </label>
      </div>
      <div class="flex gap-2">
        <textarea
          v-model="inputQuery"
          placeholder="Ask a question..."
          rows="1"
          class="flex-1 resize-none border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          @keydown="onKeydown"
        />
        <button
          :disabled="isLoading || !inputQuery.trim()"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          @click="submit"
        >
          Send
        </button>
      </div>
    </div>
  </div>
</template>
