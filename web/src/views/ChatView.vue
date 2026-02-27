<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import type { ChatEntry, ChatSession, ChatMessageRecord, WsMessage } from '@/types'
import { useWebSocket } from '@/api/ws'
import { api } from '@/api/client'
import ChatMessage from '@/components/ChatMessage.vue'

const messages = ref<ChatEntry[]>([])
const inputQuery = ref('')
const isLoading = ref(false)
const strategy = ref<'hybrid' | 'vector_only'>('hybrid')
const topK = ref(10)
const streamEnabled = ref(true)
const chatContainer = ref<HTMLElement | null>(null)
const settingsOpen = ref(false)
const activeAssistantId = ref<string | null>(null)

// Session tracking
const sessionId = ref<string>(crypto.randomUUID())
const sessions = ref<ChatSession[]>([])
const sidebarOpen = ref(false)
const sessionsLoading = ref(false)

const { connected, send, onMessage } = useWebSocket()

const textareaRows = computed(() => {
  const lines = inputQuery.value.split('\n').length
  return Math.min(Math.max(lines, 1), 6)
})

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

function findEntry(id: string): ChatEntry | undefined {
  return messages.value.find((m) => m.id === id)
}

const unsubscribe = onMessage(async (msg: WsMessage) => {
  switch (msg.type) {
    case 'sources': {
      const entry: ChatEntry = {
        id: makeId(),
        role: 'assistant',
        content: '',
        sources: msg.sources,
        strategy: msg.strategy,
        timestamp: new Date(),
      }
      messages.value.push(entry)
      activeAssistantId.value = entry.id
      await scrollToBottom()
      break
    }
    case 'token': {
      if (activeAssistantId.value) {
        const entry = findEntry(activeAssistantId.value)
        if (entry) {
          entry.content += msg.content
          await scrollToBottom()
        }
      }
      break
    }
    case 'message': {
      if (activeAssistantId.value) {
        const entry = findEntry(activeAssistantId.value)
        if (entry) {
          entry.content = msg.content
          await scrollToBottom()
        }
      }
      break
    }
    case 'done': {
      if (activeAssistantId.value) {
        const entry = findEntry(activeAssistantId.value)
        if (entry) {
          entry.latencyMs = msg.latencyMs
        }
      }
      activeAssistantId.value = null
      isLoading.value = false
      await scrollToBottom()
      break
    }
    case 'error': {
      if (activeAssistantId.value) {
        const entry = findEntry(activeAssistantId.value)
        if (entry) {
          entry.content = `Error: ${msg.content}`
        }
      } else {
        const errorEntry: ChatEntry = {
          id: makeId(),
          role: 'assistant',
          content: `Error: ${msg.content}`,
          timestamp: new Date(),
        }
        messages.value.push(errorEntry)
      }
      activeAssistantId.value = null
      isLoading.value = false
      await scrollToBottom()
      break
    }
    case 'echo': {
      // Legacy echo handler
      const assistantEntry: ChatEntry = {
        id: makeId(),
        role: 'assistant',
        content: msg.content,
        timestamp: new Date(),
      }
      messages.value.push(assistantEntry)
      isLoading.value = false
      await scrollToBottom()
      break
    }
  }
})

onUnmounted(() => {
  unsubscribe()
})

async function loadSessions() {
  sessionsLoading.value = true
  try {
    const data = await api.listSessions()
    sessions.value = data.sessions
  } catch {
    // silently ignore — sidebar just stays empty
  } finally {
    sessionsLoading.value = false
  }
}

async function loadSession(id: string) {
  try {
    const data = await api.getSession(id)
    sessionId.value = id
    messages.value = data.messages.map((m: ChatMessageRecord) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      sources: m.sources_json ? JSON.parse(m.sources_json) : undefined,
      strategy: m.strategy ?? undefined,
      latencyMs: m.latency_ms ?? undefined,
      timestamp: new Date(m.created_at),
    }))
    sidebarOpen.value = false
    await scrollToBottom()
  } catch {
    // ignore
  }
}

function newChat() {
  sessionId.value = crypto.randomUUID()
  messages.value = []
  activeAssistantId.value = null
  isLoading.value = false
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
  if (sidebarOpen.value) {
    loadSessions()
  }
}

onMounted(() => {
  loadSessions()
})

function submit() {
  const query = inputQuery.value.trim()
  if (!query || isLoading.value) return

  if (!connected.value) {
    const errorEntry: ChatEntry = {
      id: makeId(),
      role: 'assistant',
      content: 'Error: WebSocket is not connected. Please wait and try again.',
      timestamp: new Date(),
    }
    messages.value.push(errorEntry)
    scrollToBottom()
    return
  }

  const userEntry: ChatEntry = {
    id: makeId(),
    role: 'user',
    content: query,
    timestamp: new Date(),
  }
  messages.value.push(userEntry)
  inputQuery.value = ''
  isLoading.value = true
  scrollToBottom()

  send({
    type: 'chat',
    content: query,
    strategy: strategy.value,
    top_k: topK.value,
    stream: streamEnabled.value,
    session_id: sessionId.value,
  })
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
  <div class="flex h-full">
    <!-- Sidebar -->
    <Transition name="sidebar">
      <div v-if="sidebarOpen" class="w-64 border-r bg-white flex flex-col shrink-0">
        <div class="p-3 border-b flex items-center justify-between">
          <span class="text-sm font-medium text-gray-700">History</span>
          <button class="text-gray-400 hover:text-gray-600" @click="sidebarOpen = false">
            <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>
        <div class="p-2">
          <button
            class="w-full text-left px-3 py-2 text-sm rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
            @click="newChat"
          >
            + New Chat
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-2 space-y-1">
          <div v-if="sessionsLoading" class="text-xs text-gray-400 text-center py-4">Loading...</div>
          <button
            v-for="s in sessions"
            :key="s.id"
            class="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-gray-100 transition-colors truncate"
            :class="s.id === sessionId ? 'bg-gray-100 font-medium' : 'text-gray-600'"
            @click="loadSession(s.id)"
          >
            {{ s.title || 'Untitled' }}
            <span class="block text-xs text-gray-400">{{ s.message_count }} messages</span>
          </button>
          <div v-if="!sessionsLoading && sessions.length === 0" class="text-xs text-gray-400 text-center py-4">No conversations yet</div>
        </div>
      </div>
    </Transition>

    <!-- Main chat area -->
    <div class="flex flex-col flex-1 min-w-0">
    <!-- Messages -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto bg-gray-50 p-4 space-y-6">
      <!-- Empty state -->
      <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full gap-4 text-center">
        <!-- Sparkle icon -->
        <div class="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center">
          <svg class="w-6 h-6 text-blue-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.381c-.833.067-1.171 1.107-.536 1.651l3.62 3.102-1.106 4.637c-.194.813.691 1.456 1.405 1.02L10 15.591l4.069 2.485c.713.436 1.598-.207 1.404-1.02l-1.106-4.637 3.62-3.102c.635-.544.297-1.584-.536-1.65l-4.752-.382-1.83-4.401z"
              clip-rule="evenodd"
            />
          </svg>
        </div>
        <div>
          <h2 class="text-2xl font-semibold text-gray-900">How can I help?</h2>
          <p class="text-gray-500 mt-1">Ask questions about your documents</p>
        </div>
        <!-- Suggestion cards -->
        <div class="flex flex-col gap-2 w-full max-w-md">
          <button
            v-for="s in suggestions"
            :key="s"
            class="w-full border rounded-xl px-4 py-3 text-left hover:bg-gray-50 hover:border-gray-300 transition-all text-gray-700 bg-white flex items-center justify-between group/suggestion"
            @click="useSuggestion(s)"
          >
            <span>{{ s }}</span>
            <svg class="w-4 h-4 text-gray-400 shrink-0 ml-2 group-hover/suggestion:text-gray-600 transition-colors" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Messages with transition -->
      <TransitionGroup name="msg">
        <ChatMessage v-for="m in messages" :key="m.id" :entry="m" />
      </TransitionGroup>

      <!-- Loading indicator -->
      <div v-if="isLoading && !activeAssistantId" class="flex items-end gap-2">
        <!-- Assistant avatar -->
        <div class="shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center mb-1">
          <svg class="w-4 h-4 text-white" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.381c-.833.067-1.171 1.107-.536 1.651l3.62 3.102-1.106 4.637c-.194.813.691 1.456 1.405 1.02L10 15.591l4.069 2.485c.713.436 1.598-.207 1.404-1.02l-1.106-4.637 3.62-3.102c.635-.544.297-1.584-.536-1.65l-4.752-.382-1.83-4.401z"
              clip-rule="evenodd"
            />
          </svg>
        </div>
        <!-- Bouncing dots -->
        <div class="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm flex items-center gap-1.5">
          <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]"></div>
          <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]"></div>
          <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]"></div>
        </div>
      </div>
    </div>

    <!-- Input bar -->
    <div class="border-t bg-white p-4">
      <!-- Settings panel (toggleable) -->
      <div v-if="settingsOpen" class="flex items-center gap-2 mb-2">
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
        <label class="text-xs text-gray-500 flex items-center gap-1">
          <input
            v-model="streamEnabled"
            type="checkbox"
            class="rounded"
          />
          Stream
        </label>
      </div>

      <div class="flex items-end gap-2">
        <!-- Sidebar toggle -->
        <button
          class="w-9 h-9 rounded-xl flex items-center justify-center transition-colors shrink-0"
          :class="sidebarOpen ? 'bg-blue-50 text-blue-600' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'"
          @click="toggleSidebar"
          title="Chat history"
        >
          <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10zm0 5.25a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z" clip-rule="evenodd" />
          </svg>
        </button>

        <!-- Gear / settings toggle -->
        <button
          class="w-9 h-9 rounded-xl flex items-center justify-center transition-colors shrink-0"
          :class="settingsOpen ? 'bg-blue-50 text-blue-600' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'"
          @click="settingsOpen = !settingsOpen"
          title="Settings"
        >
          <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
          </svg>
        </button>

        <!-- Textarea -->
        <textarea
          v-model="inputQuery"
          placeholder="Ask a question..."
          :rows="textareaRows"
          class="flex-1 resize-none border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          @keydown="onKeydown"
        />

        <!-- Connection status dot -->
        <div
          class="w-2.5 h-2.5 rounded-full shrink-0 self-center"
          :class="connected ? 'bg-green-500' : 'bg-red-400'"
          :title="connected ? 'WebSocket connected' : 'WebSocket disconnected'"
        />

        <!-- Send button (icon-only) -->
        <button
          :disabled="isLoading || !inputQuery.trim()"
          class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 transition-colors disabled:cursor-not-allowed"
          :class="inputQuery.trim() && !isLoading ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-100 text-gray-400'"
          @click="submit"
        >
          <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>

      <!-- Keyboard hint -->
      <p class="text-xs text-gray-400 mt-1">Enter to send · Shift+Enter for new line</p>
    </div>
    </div><!-- /main chat area -->
  </div>
</template>

<style scoped>
.msg-enter-active {
  transition: all 0.3s ease-out;
}
.msg-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.sidebar-enter-active,
.sidebar-leave-active {
  transition: all 0.2s ease;
}
.sidebar-enter-from,
.sidebar-leave-to {
  opacity: 0;
  transform: translateX(-16px);
}
</style>
