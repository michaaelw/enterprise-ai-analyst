import express from 'express'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import healthRoutes from './routes/health.js'
import apiRoutes from './routes/api.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const app = express()
const PORT = parseInt(process.env.PORT || '3000', 10)

app.use(express.json({ limit: '10mb' }))

// BFF health check (Node-level)
app.use(healthRoutes)

// Proxy /api/* → FastAPI (strip /api prefix)
app.use('/api', apiRoutes)

// Production: serve built SPA
if (process.env.NODE_ENV === 'production') {
  const clientDir = resolve(__dirname, '..', 'dist', 'client')
  app.use(express.static(clientDir))
  app.get('*', (_req, res) => {
    res.sendFile(resolve(clientDir, 'index.html'))
  })
}

app.listen(PORT, () => {
  console.log(`BFF listening on http://localhost:${PORT}`)
})
