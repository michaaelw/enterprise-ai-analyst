import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
    },
    {
      path: '/ingest',
      name: 'ingest',
      component: () => import('@/views/IngestView.vue'),
    },
  ],
})

export default router
