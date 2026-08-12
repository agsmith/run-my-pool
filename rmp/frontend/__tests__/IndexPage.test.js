import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import IndexPage from '../pages/index'

// ---------------------------------------------------------------------------
// AuthContext mock
// ---------------------------------------------------------------------------
jest.mock('../context/AuthContext', () => ({
  useAuth: jest.fn(),
}))
import { useAuth } from '../context/AuthContext'

// ---------------------------------------------------------------------------
// Router mock
// ---------------------------------------------------------------------------
const mockPush = jest.fn()
const mockReplace = jest.fn()

jest.mock('next/router', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    query: {},
    pathname: '/',
  }),
}))

// ---------------------------------------------------------------------------
// globalStyles mock
// ---------------------------------------------------------------------------
jest.mock('../styles/globalStyles', () => ({
  mobileStyles: {},
  getResponsiveStyle: () => ({}),
  touchStyles: {},
}))

beforeEach(() => {
  mockPush.mockClear()
  mockReplace.mockClear()
  // Default: unauthenticated
  useAuth.mockReturnValue({ user: null })
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('IndexPage', () => {
  test('renders the main "Run My Pool" heading in the hero section', () => {
    render(<IndexPage />)

    // The h1 contains the brand name
    const heading = screen.getByRole('heading', { level: 1 })
    expect(heading).toHaveTextContent(/run my pool/i)
  })

  test('shows the Get Started Free link when user is not authenticated', () => {
    render(<IndexPage />)

    const link = screen.getByRole('link', { name: /get started free/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/pricing')
  })

  test('shows a Login link in the header for unauthenticated users', () => {
    render(<IndexPage />)

    const loginLink = screen.getByRole('link', { name: /^login$/i })
    expect(loginLink).toBeInTheDocument()
    expect(loginLink).toHaveAttribute('href', '/login')
  })

  test('makes the splash page the creation entry point for logged-in users', () => {
    useAuth.mockReturnValue({ user: { id: '1', email: 'a@b.com' } })

    render(<IndexPage />)

    expect(screen.getByRole('link', { name: /get started free/i })).toHaveAttribute(
      'href',
      '/create-pool?source=splash',
    )
    expect(mockPush).not.toHaveBeenCalled()
  })

  test('keeps the splash content visible when user is authenticated', () => {
    useAuth.mockReturnValue({ user: { id: '1', email: 'a@b.com' } })

    render(<IndexPage />)

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/run my pool/i)
    expect(screen.queryByText(/redirecting/i)).not.toBeInTheDocument()
  })

  test('renders the "Highly Configurable" feature heading', () => {
    render(<IndexPage />)

    // The h2 subtitle also contains this text, so scope to h4 level
    const headings = screen.getAllByRole('heading', { name: /highly configurable/i })
    const h4 = headings.find((el) => el.tagName === 'H4')
    expect(h4).toBeInTheDocument()
  })

  test('renders the "Affordable" feature heading', () => {
    render(<IndexPage />)

    // The h2 subtitle also contains "Affordable", scope to h4
    const headings = screen.getAllByRole('heading', { name: /^affordable$/i })
    const h4 = headings.find((el) => el.tagName === 'H4')
    expect(h4).toBeInTheDocument()
  })

  test('renders the "Mobile App" feature heading', () => {
    render(<IndexPage />)

    expect(
      screen.getByRole('heading', { name: /mobile app/i })
    ).toBeInTheDocument()
  })

  test('renders the "Why Choose Run My Pool?" features section heading', () => {
    render(<IndexPage />)

    expect(
      screen.getByRole('heading', { name: /why choose run my pool/i })
    ).toBeInTheDocument()
  })

  test('renders the hero subtitle describing the system', () => {
    render(<IndexPage />)

    expect(
      screen.getByText(/highly configurable, affordable, scalable pool management system/i)
    ).toBeInTheDocument()
  })
})
