import { Router } from 'express'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

const router = Router()

async function proxyToFastAPI(
  fastApiPath: string,
  req: import('express').Request,
  res: import('express').Response,
) {
  try {
    const url = `${FASTAPI_URL}${fastApiPath}`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    const fetchOptions: RequestInit = {
      method: req.method,
      headers,
    }

    if (req.method !== 'GET' && req.method !== 'HEAD') {
      fetchOptions.body = JSON.stringify(req.body)
    }

    const response = await fetch(url, fetchOptions)
    const contentType = response.headers.get('content-type') || ''

    res.status(response.status)

    if (contentType.includes('application/json')) {
      const data = await response.json()
      res.json(data)
    } else {
      const text = await response.text()
      res.set('Content-Type', contentType).send(text)
    }
  } catch (err) {
    console.error(`FastAPI proxy error [${fastApiPath}]:`, err)
    res.status(502).json({
      error: 'FastAPI unavailable',
      detail: err instanceof Error ? err.message : String(err),
    })
  }
}

// Explicit route handlers
router.get('/health', (req, res) => proxyToFastAPI('/health', req, res))
router.get('/health/ready', (req, res) => proxyToFastAPI('/health/ready', req, res))
router.post('/query', (req, res) => proxyToFastAPI('/query', req, res))
router.post('/ingest', (req, res) => proxyToFastAPI('/ingest', req, res))
router.post('/retrieve', (req, res) => proxyToFastAPI('/retrieve', req, res))
router.post('/generate', (req, res) => proxyToFastAPI('/generate', req, res))
router.post('/query/stream', (req, res) => proxyToFastAPI('/query/stream', req, res))

// Chat history
router.get('/history/sessions', (req, res) => proxyToFastAPI('/history/sessions', req, res))
router.get('/history/sessions/:id', (req, res) => proxyToFastAPI(`/history/sessions/${req.params.id}`, req, res))
router.post('/history/messages', (req, res) => proxyToFastAPI('/history/messages', req, res))

export default router
