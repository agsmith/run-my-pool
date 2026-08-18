import manifest from '../public/manifest.json'

describe('PWA manifest', () => {
  test('launches inside the authenticated dashboard flow', () => {
    expect(manifest.start_url).toBe('/dashboard')
    expect(manifest.scope).toBe('/')
  })
})
