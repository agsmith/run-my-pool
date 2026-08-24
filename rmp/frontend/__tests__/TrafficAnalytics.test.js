import '@testing-library/jest-dom'
import { render } from '@testing-library/react'
import TrafficAnalytics, { CLOUDFLARE_BEACON_URL } from '../components/TrafficAnalytics'

jest.mock('next/script', () => ({
  __esModule: true,
  default: function MockScript(props) {
    return <script {...props} />
  },
}))

describe('TrafficAnalytics', () => {
  const originalToken = process.env.NEXT_PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN

  afterEach(() => {
    if (originalToken === undefined) delete process.env.NEXT_PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN
    else process.env.NEXT_PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN = originalToken
  })

  test('does not load a third-party script when no site token is configured', () => {
    delete process.env.NEXT_PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN
    const { container } = render(<TrafficAnalytics />)
    expect(container).toBeEmptyDOMElement()
  })

  test('loads the privacy-first beacon when a site token is configured', () => {
    process.env.NEXT_PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN = ' runmypool-token '
    render(<TrafficAnalytics />)

    const beacon = document.querySelector('#cloudflare-web-analytics')
    expect(beacon).toHaveAttribute('src', CLOUDFLARE_BEACON_URL)
    expect(beacon).toHaveAttribute('type', 'module')
    expect(beacon).toHaveAttribute('data-cf-beacon', JSON.stringify({ token: 'runmypool-token' }))
  })
})
