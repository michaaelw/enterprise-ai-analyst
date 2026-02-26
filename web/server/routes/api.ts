import { Router, Request } from 'express'
import { createProxyMiddleware, fixRequestBody } from 'http-proxy-middleware'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

const router = Router()

router.use(
  '/',
  createProxyMiddleware<Request>({
    target: FASTAPI_URL,
    changeOrigin: true,
    on: {
      proxyReq: fixRequestBody,
    },
  }),
)

export default router
