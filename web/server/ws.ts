import type { IncomingMessage } from 'http'
import type * as http from 'http'
import { WebSocketServer, WebSocket } from 'ws'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

interface ChatRequest {
  type: string
  content: string
  strategy?: string
  top_k?: number
  stream?: boolean
}

function sendJson(ws: WebSocket, data: unknown): void {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data))
  }
}

function parseSSEEvents(buffer: string): { events: Array<{ event: string; data: string }>; remainder: string } {
  const events: Array<{ event: string; data: string }> = []
  const blocks = buffer.split('\n\n')
  const remainder = blocks.pop() ?? ''

  for (const block of blocks) {
    if (!block.trim()) continue
    let event = ''
    let data = ''
    for (const line of block.split('\n')) {
      if (line.startsWith('event: ')) event = line.slice(7)
      else if (line.startsWith('data: ')) data = line.slice(6)
    }
    if (event && data) {
      events.push({ event, data })
    }
  }

  return { events, remainder }
}

async function handleChat(ws: WebSocket, msg: ChatRequest): Promise<void> {
  const query = msg.content
  const strategy = msg.strategy ?? 'hybrid'
  const topK = msg.top_k ?? 10
  const stream = msg.stream ?? true
  const totalStart = Date.now()

  // Step 1: Call /retrieve
  let context: string
  try {
    const retrieveRes = await fetch(`${FASTAPI_URL}/retrieve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, strategy, top_k: topK }),
    })

    if (!retrieveRes.ok) {
      const errText = await retrieveRes.text()
      sendJson(ws, { type: 'error', content: `Retrieval failed: ${retrieveRes.status} ${errText}` })
      return
    }

    const retrieveData = await retrieveRes.json()
    context = retrieveData.context

    sendJson(ws, {
      type: 'sources',
      sources: retrieveData.sources,
      query: retrieveData.query,
      strategy: retrieveData.strategy,
    })
  } catch (err) {
    sendJson(ws, { type: 'error', content: `Retrieval error: ${err instanceof Error ? err.message : String(err)}` })
    return
  }

  // Step 2: Build prompt
  const prompt = `Based on the following context, answer the question. If the context doesn't contain enough information, say so.

Context:
${context}

Question: ${query}

Answer:`

  // Step 3: Call /generate
  const controller = new AbortController()
  const onClose = () => controller.abort()
  ws.on('close', onClose)

  try {
    const generateRes = await fetch(`${FASTAPI_URL}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, stream }),
      signal: controller.signal,
    })

    if (!generateRes.ok) {
      const errText = await generateRes.text()
      sendJson(ws, { type: 'error', content: `Generation failed: ${generateRes.status} ${errText}` })
      return
    }

    if (!stream) {
      // Non-streaming: read full JSON response
      const genData = await generateRes.json()
      sendJson(ws, { type: 'message', content: genData.answer })
      const latencyMs = Date.now() - totalStart
      sendJson(ws, { type: 'done', latencyMs })
    } else {
      // Streaming: parse SSE events
      const body = generateRes.body
      if (!body) {
        sendJson(ws, { type: 'error', content: 'No response body from generate endpoint' })
        return
      }

      const reader = body.getReader()
      const decoder = new TextDecoder()
      let sseBuffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        sseBuffer += decoder.decode(value, { stream: true })
        const parsed = parseSSEEvents(sseBuffer)
        sseBuffer = parsed.remainder

        for (const evt of parsed.events) {
          if (evt.event === 'token') {
            const tokenData = JSON.parse(evt.data)
            sendJson(ws, { type: 'token', content: tokenData.token })
          } else if (evt.event === 'done') {
            const doneData = JSON.parse(evt.data)
            const latencyMs = Date.now() - totalStart
            sendJson(ws, { type: 'done', latencyMs })
          } else if (evt.event === 'error') {
            const errData = JSON.parse(evt.data)
            sendJson(ws, { type: 'error', content: errData.error })
          }
        }
      }

      // If no done event was received from FastAPI, send one
      // (this handles the case where the stream ends without an explicit done)
    }
  } catch (err: unknown) {
    if (err instanceof Error && err.name === 'AbortError') {
      console.log('[WS] Fetch aborted (client disconnected)')
      return
    }
    sendJson(ws, { type: 'error', content: `Generation error: ${err instanceof Error ? err.message : String(err)}` })
  } finally {
    ws.off('close', onClose)
  }
}

export function attachWebSocket(server: http.Server): void {
  const wss = new WebSocketServer({ server, path: '/ws' })

  wss.on('connection', (ws: WebSocket, _req: IncomingMessage) => {
    console.log('[WS] Client connected')
    let streaming = false

    ws.on('message', async (data: Buffer | ArrayBuffer | Buffer[]) => {
      try {
        const raw = data.toString()
        const msg: ChatRequest = JSON.parse(raw)

        if (msg.type === 'chat') {
          if (streaming) {
            sendJson(ws, { type: 'error', content: 'A query is already in progress' })
            return
          }
          streaming = true
          try {
            await handleChat(ws, msg)
          } finally {
            streaming = false
          }
        }
      } catch (err) {
        console.error('[WS] Failed to handle message:', err)
        sendJson(ws, { type: 'error', content: 'Failed to process message' })
      }
    })

    ws.on('close', () => {
      console.log('[WS] Client disconnected')
    })

    ws.on('error', (err: Error) => {
      console.error('[WS] Socket error:', err)
    })
  })

  console.log('[WS] WebSocket server attached on path /ws')
}
