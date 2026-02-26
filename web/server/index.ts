import express from 'express'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { readFileSync } from 'fs'
import healthRoutes from './routes/health.js'
import apiRoutes from './routes/api.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const isDev = process.env.NODE_ENV !== 'production'
const PORT = parseInt(process.env.PORT || '3000', 10)

async function createApp() {
  const app = express()

  app.use(express.json({ limit: '10mb' }))

  // BFF health check (Node-level)
  app.use(healthRoutes)

  // API routes → FastAPI
  app.use('/api', apiRoutes)

  let vite: any

  if (isDev) {
    const { createServer } = await import('vite')
    vite = await createServer({
      server: { middlewareMode: true },
      appType: 'custom',
    })
    app.use(vite.middlewares)
  } else {
    const clientDir = resolve(__dirname, '..', 'dist', 'client')
    app.use(express.static(clientDir))
  }

  // SPA fallback — serve index.html for all non-API, non-asset routes
  app.get('*', async (req, res) => {
    const url = req.originalUrl

    if (isDev) {
      const htmlPath = resolve(__dirname, '..', 'index.html')
      let html = readFileSync(htmlPath, 'utf-8')
      html = await vite.transformIndexHtml(url, html)
      res.status(200).set({ 'Content-Type': 'text/html' }).send(html)
    } else {
      const clientDir = resolve(__dirname, '..', 'dist', 'client')
      res.sendFile(resolve(clientDir, 'index.html'))
    }
  })

  app.listen(PORT, () => {
    console.log(`BFF listening on http://localhost:${PORT}`)
  })
}

createApp()
