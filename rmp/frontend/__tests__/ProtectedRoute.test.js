import '@testing-library/jest-dom'
import { render, screen, waitFor } from '@testing-library/react'
import ProtectedRoute from '../components/ProtectedRoute'

// ---------------------------------------------------------------------------
// AuthContext mock — controls useAuth return value per test
// ---------------------------------------------------------------------------
jest.mock('../context/AuthContext', () => ({
  useAuth: jest.fn(),
}))
import { useAuth } from '../context/AuthContext'

// ---------------------------------------------------------------------------
// Router mock
// ---------------------------------------------------------------------------
const mockReplace = jest.fn()
let mockAsPath = '/'

jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: mockReplace,
    query: {},
    pathname: '/',
    asPath: mockAsPath,
  }),
}))

beforeEach(() => {
  mockReplace.mockClear()
  mockAsPath = '/'
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('ProtectedRoute', () => {
  test('renders children when user is authenticated', async () => {
    useAuth.mockReturnValue({ user: { id: '1', email: 'a@b.com' }, loading: false })

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )

    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  test('shows loading indicator while auth is resolving', () => {
    useAuth.mockReturnValue({ user: null, loading: true })

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  test('redirects to /login when user is null and not loading', async () => {
    useAuth.mockReturnValue({ user: null, loading: false })

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login')
    })
  })

  test('preserves a pool invitation when authentication is required', async () => {
    mockAsPath = '/leagues?invite=pool-1'
    useAuth.mockReturnValue({ user: null, loading: false })

    render(<ProtectedRoute><div>Protected Content</div></ProtectedRoute>)

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        `/login?next=${encodeURIComponent('/leagues?invite=pool-1')}`,
      )
    })
  })

  test('does not render children when user is null and not loading', () => {
    useAuth.mockReturnValue({ user: null, loading: false })

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  test('does not render children while loading is true', () => {
    useAuth.mockReturnValue({ user: null, loading: true })

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  test('does not redirect when user is authenticated', async () => {
    useAuth.mockReturnValue({ user: { id: '1', email: 'a@b.com' }, loading: false })

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )

    // Give the effect a chance to fire — it should NOT have redirected
    await waitFor(() => {
      expect(mockReplace).not.toHaveBeenCalled()
    })
  })
})
