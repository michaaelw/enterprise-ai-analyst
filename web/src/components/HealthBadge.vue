<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '@/api/client'

type Status = 'connected' | 'degraded' | 'disconnected'

const status = ref<Status>('disconnected')
let timer: ReturnType<typeof setInterval>

async function check() {
  try {
    const res = await api.healthReady()
    status.value = res.status === 'ready' ? 'connected' : 'degraded'
  } catch {
    status.value = 'disconnected'
  }
}

onMounted(() => {
  check()
  timer = setInterval(check, 30_000)
})

onUnmounted(() => clearInterval(timer))

const colors: Record<Status, string> = {
  connected: 'bg-green-400',
  degraded: 'bg-yellow-400',
  disconnected: 'bg-red-400',
}

const labels: Record<Status, string> = {
  connected: 'Connected',
  degraded: 'Degraded',
  disconnected: 'Disconnected',
}
</script>

<template>
  <div class="flex items-center gap-2 text-xs">
    <span :class="colors[status]" class="w-2 h-2 rounded-full" />
    <span class="text-gray-300">{{ labels[status] }}</span>
  </div>
</template>
