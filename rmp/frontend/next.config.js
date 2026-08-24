const withSerwist = require('@serwist/next').default({
  swSrc: 'service-worker/index.js',
  swDest: 'public/sw.js',
  disable: process.env.NODE_ENV === 'development',
  register: true,
  additionalPrecacheEntries: [{ url: '/offline', revision: 'offline-v1' }],
})

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  poweredByHeader: false,
  async headers() {
    const development = process.env.NODE_ENV === 'development'
    const contentSecurityPolicy = [
      "default-src 'self'",
      "base-uri 'self'",
      "connect-src 'self' https://runmypool.net https://cloudflareinsights.com",
      "font-src 'self' data:",
      "form-action 'self'",
      "frame-ancestors 'none'",
      "img-src 'self' data: https:",
      "object-src 'none'",
      `script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com${development ? " 'unsafe-eval'" : ''}`,
      "style-src 'self' 'unsafe-inline'",
      ...(development ? [] : ["upgrade-insecure-requests"]),
    ].join('; ')
    return [{
      source: '/:path*',
      headers: [
        { key: 'Content-Security-Policy', value: contentSecurityPolicy },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
      ],
    }]
  },
}

module.exports = withSerwist(nextConfig)
