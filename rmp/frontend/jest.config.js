const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Path to Next.js app — loads next.config.js and .env files
  dir: './',
})

const customJestConfig = {
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testMatch: [
    '**/__tests__/**/*.[jt]s?(x)',
    '**/?(*.)+(spec|test).[jt]s?(x)',
  ],
  testPathIgnorePatterns: ['/node_modules/', '/e2e/'],
  collectCoverageFrom: [
    'components/**/*.{js,jsx}',
    'context/**/*.{js,jsx}',
    'pages/**/*.{js,jsx}',
    '!pages/_app.js',
    '!pages/api/**',
    '!**/*.test.{js,jsx}',
    '!**/__tests__/**',
  ],
  coverageThreshold: {
    global: {
      statements: 50,
      branches: 45,
      functions: 40,
      lines: 50,
    },
  },
}

module.exports = createJestConfig(customJestConfig)
