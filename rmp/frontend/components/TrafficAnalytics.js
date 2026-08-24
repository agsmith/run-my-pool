import Script from 'next/script'

export const CLOUDFLARE_BEACON_URL = 'https://static.cloudflareinsights.com/beacon.min.js'

export default function TrafficAnalytics() {
  const token = process.env.NEXT_PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN?.trim()

  if (!token) return null

  return (
    <Script
      id="cloudflare-web-analytics"
      type="module"
      src={CLOUDFLARE_BEACON_URL}
      strategy="afterInteractive"
      data-cf-beacon={JSON.stringify({ token })}
    />
  )
}
