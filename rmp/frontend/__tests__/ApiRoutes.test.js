import '@testing-library/jest-dom'
import healthHandler from '../pages/api/health'
import liveHandler from '../pages/api/live'
import readyHandler from '../pages/api/ready'

// ---------------------------------------------------------------------------
// Shared mock factory
// ---------------------------------------------------------------------------
function mockReqRes(method = 'GET') {
  const req = { method }
  const res = {
    status: jest.fn().mockReturnThis(),
    json: jest.fn().mockReturnThis(),
    setHeader: jest.fn().mockReturnThis(),
    end: jest.fn(),
  }
  return { req, res }
}

// ---------------------------------------------------------------------------
// GET /api/health
// ---------------------------------------------------------------------------
describe('GET /api/health', () => {
  test('returns HTTP 200 for a successful health check', () => {
    const { req, res } = mockReqRes()

    healthHandler(req, res)

    expect(res.status).toHaveBeenCalledWith(200)
  })

  test('responds with status "healthy"', () => {
    const { req, res } = mockReqRes()

    healthHandler(req, res)

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'healthy' })
    )
  })

  test('includes the service name "runmypool-frontend" in the response', () => {
    const { req, res } = mockReqRes()

    healthHandler(req, res)

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({ service: 'runmypool-frontend' })
    )
  })

  test('includes a timestamp in the response', () => {
    const { req, res } = mockReqRes()

    healthHandler(req, res)

    const payload = res.json.mock.calls[0][0]
    expect(payload).toHaveProperty('timestamp')
    expect(typeof payload.timestamp).toBe('string')
  })

  test('sets Cache-Control header to prevent caching', () => {
    const { req, res } = mockReqRes()

    healthHandler(req, res)

    expect(res.setHeader).toHaveBeenCalledWith(
      'Cache-Control',
      'no-cache, no-store, must-revalidate'
    )
  })
})

// ---------------------------------------------------------------------------
// GET /api/live
// ---------------------------------------------------------------------------
describe('GET /api/live', () => {
  test('returns HTTP 200 for the liveness check', () => {
    const { req, res } = mockReqRes()

    liveHandler(req, res)

    expect(res.status).toHaveBeenCalledWith(200)
  })

  test('responds with status "alive"', () => {
    const { req, res } = mockReqRes()

    liveHandler(req, res)

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'alive' })
    )
  })

  test('includes a timestamp in the liveness response', () => {
    const { req, res } = mockReqRes()

    liveHandler(req, res)

    const payload = res.json.mock.calls[0][0]
    expect(payload).toHaveProperty('timestamp')
    expect(typeof payload.timestamp).toBe('string')
  })

  test('responds to a GET method request', () => {
    const { req, res } = mockReqRes('GET')

    liveHandler(req, res)

    expect(res.status).toHaveBeenCalledWith(200)
    expect(res.json).toHaveBeenCalledTimes(1)
  })

  test('sets Cache-Control header', () => {
    const { req, res } = mockReqRes()

    liveHandler(req, res)

    expect(res.setHeader).toHaveBeenCalledWith(
      'Cache-Control',
      'no-cache, no-store, must-revalidate'
    )
  })
})

// ---------------------------------------------------------------------------
// GET /api/ready
// ---------------------------------------------------------------------------
describe('GET /api/ready', () => {
  test('returns HTTP 200 for the readiness check', () => {
    const { req, res } = mockReqRes()

    readyHandler(req, res)

    expect(res.status).toHaveBeenCalledWith(200)
  })

  test('responds with status "ready"', () => {
    const { req, res } = mockReqRes()

    readyHandler(req, res)

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'ready' })
    )
  })

  test('includes the service name "runmypool-frontend" in the readiness response', () => {
    const { req, res } = mockReqRes()

    readyHandler(req, res)

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({ service: 'runmypool-frontend' })
    )
  })

  test('includes a checks object with server status', () => {
    const { req, res } = mockReqRes()

    readyHandler(req, res)

    const payload = res.json.mock.calls[0][0]
    expect(payload).toHaveProperty('checks')
    expect(payload.checks).toMatchObject({ server: 'ok' })
  })

  test('responds to a GET method request', () => {
    const { req, res } = mockReqRes('GET')

    readyHandler(req, res)

    expect(res.status).toHaveBeenCalledWith(200)
    expect(res.json).toHaveBeenCalledTimes(1)
  })

  test('sets Cache-Control header to prevent caching', () => {
    const { req, res } = mockReqRes()

    readyHandler(req, res)

    expect(res.setHeader).toHaveBeenCalledWith(
      'Cache-Control',
      'no-cache, no-store, must-revalidate'
    )
  })
})
