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
}

module.exports = withSerwist(nextConfig)
