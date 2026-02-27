export interface QueryRequest {
  query: string
  top_k?: number
  strategy?: 'hybrid' | 'vector_only' | 'auto'
}

export interface ChunkData {
  id: string
  document_id: string
  content: string
  token_count: number
  index: number
  metadata: Record<string, unknown>
}

export interface RetrievalResultData {
  chunk: ChunkData
  score: number
  source: string
}

export interface QueryResponse {
  answer: string
  sources: RetrievalResultData[]
  query: string
  strategy: string
  latency_ms: number
}

export interface IngestRequest {
  content: string
  source?: string
  metadata?: Record<string, unknown>
}

export interface IngestResponse {
  document_id: string
  chunks_created: number
}

export interface HealthResponse {
  status: string
  checks?: Record<string, string>
}

export interface ChatEntry {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: RetrievalResultData[]
  latencyMs?: number
  strategy?: string
  timestamp: Date
  agentStatus?: { agent: string; phase: string; message: string }
}

// WebSocket message types (discriminated union)
export interface WsStatusMessage { type: 'status'; agent: string; phase: string; message: string }
export interface WsSourcesMessage { type: 'sources'; sources: RetrievalResultData[]; query: string; strategy: string }
export interface WsTokenMessage { type: 'token'; content: string }
export interface WsFullMessage { type: 'message'; content: string }
export interface WsDoneMessage { type: 'done'; latencyMs: number }
export interface WsErrorMessage { type: 'error'; content: string }
export interface WsEchoMessage { type: 'echo'; content: string }

export type WsMessage = WsStatusMessage | WsSourcesMessage | WsTokenMessage | WsFullMessage | WsDoneMessage | WsErrorMessage | WsEchoMessage

export interface WsChatRequest { type: 'chat'; content: string; strategy?: string; top_k?: number; stream?: boolean; session_id?: string }

// Chat history types
export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ChatSessionListResponse {
  sessions: ChatSession[]
}

export interface ChatMessageRecord {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  sources_json: string
  strategy?: string
  latency_ms?: number
  created_at: string
}

export interface ChatHistoryResponse {
  session: ChatSession
  messages: ChatMessageRecord[]
}
