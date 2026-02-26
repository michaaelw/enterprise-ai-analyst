import type { QueryRequest, QueryResponse, IngestRequest, IngestResponse, HealthResponse } from '@/types'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export const api = {
  query(body: QueryRequest): Promise<QueryResponse> {
    return request('/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  },

  ingest(body: IngestRequest): Promise<IngestResponse> {
    return request('/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  },

  health(): Promise<HealthResponse> {
    return request('/health')
  },

  healthReady(): Promise<HealthResponse> {
    return request('/health/ready')
  },
}
