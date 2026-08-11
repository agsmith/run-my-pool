import '@testing-library/jest-dom'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NavBar from '../components/NavBar'

// ---------------------------------------------------------------------------
// AuthContext mock
// ---------------------------------------------------------------------------
jest.mock('../context/AuthContext', () => ({
  useAuth: jest.fn(),
}))
import { useAuth } from '../context/AuthContext'

// ---------------------------------------------------------------------------
// Router mock — NavBar uses next/link which depends on the router
// ---------------------------------------------------------------------------
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    query: {},
    pathname: '/',
  }),
}))

beforeEach(() => {
  // Default to unauthenticated state
  useAuth.mockReturnValue({ user: null, logout: jest.fn() })
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('NavBar', () => {
  test('renders global navigation links for Dashboard and Leagues', () => {
    render(<NavBar />)

    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /leagues/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /message board/i })).not.toBeInTheDocument()
  })

  test('keeps administration out of the global navigation', () => {
    useAuth.mockReturnValue({ user: { email: 'commissioner@example.com' }, logout: jest.fn() })
    render(<NavBar />)

    expect(screen.queryByRole('link', { name: /^admin$/i })).not.toBeInTheDocument()
  })

  test('shows Login and Register links when user is not authenticated', () => {
    useAuth.mockReturnValue({ user: null, logout: jest.fn() })

    render(<NavBar />)

    expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /register/i })).toBeInTheDocument()
  })

  test('does not show Logout button when user is not authenticated', () => {
    useAuth.mockReturnValue({ user: null, logout: jest.fn() })

    render(<NavBar />)

    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument()
  })

  test('shows Logout button when user is authenticated', () => {
    useAuth.mockReturnValue({ user: { email: 'a@b.com' }, logout: jest.fn() })

    render(<NavBar />)

    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })

  test('shows Profile link when user is authenticated', () => {
    useAuth.mockReturnValue({ user: { email: 'a@b.com' }, logout: jest.fn() })

    render(<NavBar />)

    expect(screen.getByRole('link', { name: /profile/i })).toBeInTheDocument()
  })

  test('does not show Profile link when user is not authenticated', () => {
    useAuth.mockReturnValue({ user: null, logout: jest.fn() })

    render(<NavBar />)

    expect(screen.queryByRole('link', { name: /profile/i })).not.toBeInTheDocument()
  })

  test('calls logout from auth context when Logout button is clicked', async () => {
    const mockLogout = jest.fn()
    useAuth.mockReturnValue({ user: { email: 'a@b.com' }, logout: mockLogout })

    const user = userEvent.setup()
    render(<NavBar />)

    await user.click(screen.getByRole('button', { name: /logout/i }))

    expect(mockLogout).toHaveBeenCalledTimes(1)
  })

  test('hamburger menu toggle button is present in the DOM', () => {
    render(<NavBar />)

    // The button always exists in the DOM; CSS controls its visibility.
    // RTL's accessible-role query respects display:none and excludes it on desktop,
    // so query by the rendered text content directly.
    expect(screen.getByText('☰')).toBeInTheDocument()
  })

  test('hamburger button toggles icon when clicked', async () => {
    const user = userEvent.setup()
    render(<NavBar />)

    // Initially shows ☰ — click via the DOM element directly since it is
    // visually hidden in the jsdom desktop viewport.
    const toggleBtn = screen.getByText('☰').closest('button')
    await user.click(toggleBtn)

    // After click shows ✕
    expect(screen.getByText('✕')).toBeInTheDocument()
  })

  test('uses the collapsed menu at tablet widths', () => {
    act(() => {
      window.innerWidth = 900
      window.dispatchEvent(new Event('resize'))
    })
    render(<NavBar />)

    expect(screen.getByRole('button', { name: /toggle navigation menu/i })).toBeVisible()
    expect(screen.getByRole('button', { name: /toggle navigation menu/i })).toHaveAttribute('aria-expanded', 'false')
  })

  test('hides Login and Register links when user is authenticated', () => {
    useAuth.mockReturnValue({ user: { email: 'a@b.com' }, logout: jest.fn() })

    render(<NavBar />)

    expect(screen.queryByRole('link', { name: /^login$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /^register$/i })).not.toBeInTheDocument()
  })
})
