import { Router } from 'express'

const router = Router()

router.get('/bff/health', (_req, res) => {
  res.json({ status: 'ok', service: 'bff' })
})

export default router
