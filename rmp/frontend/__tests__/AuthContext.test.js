import '@testing-library/jest-dom'
import { render, screen, act, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from '../context/AuthContext'

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
// Fetch mock
// ---------------------------------------------------------------------------
global.fetch = jest.fn()

beforeEach(() => {
  fetch.mockClear()
  mockPush.mockClear()
  mockReplace.mockClear()
  localStorage.clear()
})

// ---------------------------------------------------------------------------
// Helper components
// ---------------------------------------------------------------------------
function TestConsumer() {
  const { user, token, loading } = useAuth()
  return (
    <div>
      <span data-testid="user">{user ? user.email : 'null'}</span>
      <span data-testid="token">{token ?? 'null'}</span>
      <span data-testid="loading">{String(loading)}</span>
    </div>
  )
}

function LoginConsumer({ email, password }) {
  const { login, loading } = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <button
        data-testid="login-btn"
        onClick={() => login(email, password).catch(() => {})}
      >
        Login
      </button>
    </div>
  )
}

function LogoutConsumer() {
  const { logout, user } = useAuth()
  return (
    <div>
      <span data-testid="user">{user ? user.email : 'null'}</span>
      <button data-testid="logout-btn" onClick={logout}>
        Logout
      </button>
    </div>
  )
}

function renderWithAuth(ui = <TestConsumer />) {
  return render(<AuthProvider>{ui}</AuthProvider>)
}

// ---------------------------------------------------------------------------
// describe: AuthProvider
// ---------------------------------------------------------------------------
describe('AuthProvider', () => {
  test('provides null user and null token on fresh mount', async () => {
    renderWithAuth()

    // Wait for the loading useEffect to finish
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user')).toHaveTextContent('null')
    expect(screen.getByTestId('token')).toHaveTextContent('null')
  })

  test('rehydrates user and token from localStorage on mount', async () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('user', JSON.stringify({ id: '1', email: 'a@b.com' }))

    renderWithAuth()

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user')).toHaveTextContent('a@b.com')
    expect(screen.getByTestId('token')).toHaveTextContent('test-token')
  })

  test('loading transitions to false after mount', async () => {
    renderWithAuth()

    // The useEffect fires synchronously in jsdom; loading resolves to false.
    // Assert that by the time the component is stable, loading is false.
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })
  })
})

// ---------------------------------------------------------------------------
// describe: login function
// ---------------------------------------------------------------------------
describe('login function', () => {
  test('calls /auth/login then /auth/me and stores token in localStorage', async () => {
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'tok' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: '1', email: 'a@b.com' }),
      })

    renderWithAuth(<LoginConsumer email="a@b.com" password="Pass1!ab" />)

    await act(async () => {
      screen.getByTestId('login-btn').click()
    })

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe('tok')
    })

    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch.mock.calls[0][0]).toContain('/auth/login')
    expect(fetch.mock.calls[1][0]).toContain('/auth/me')
  })

  test('stores user info from /auth/me in localStorage', async () => {
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'tok' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: '1', email: 'a@b.com' }),
      })

    renderWithAuth(<LoginConsumer email="a@b.com" password="Pass1!ab" />)

    await act(async () => {
      screen.getByTestId('login-btn').click()
    })

    await waitFor(() => {
      expect(localStorage.getItem('user')).toBe(
        JSON.stringify({ id: '1', email: 'a@b.com' })
      )
    })
  })

  test('navigates to /dashboard on successful login', async () => {
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'tok' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: '1', email: 'a@b.com' }),
      })

    renderWithAuth(<LoginConsumer email="a@b.com" password="Pass1!ab" />)

    await act(async () => {
      screen.getByTestId('login-btn').click()
    })

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/dashboard')
    })
  })

  test('throws on bad credentials when server returns not-ok', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Invalid credentials' }),
    })

    const onError = jest.fn()

    function ErrorConsumer() {
      const { login } = useAuth()
      return (
        <button
          data-testid="login-btn"
          onClick={() => login('bad@user.com', 'WrongPass1!').catch(onError)}
        >
          Login
        </button>
      )
    }

    renderWithAuth(<ErrorConsumer />)

    await act(async () => {
      screen.getByTestId('login-btn').click()
    })

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({ message: 'Invalid credentials' })
      )
    })
  })
})

// ---------------------------------------------------------------------------
// describe: logout function
// ---------------------------------------------------------------------------
describe('logout function', () => {
  test('logout clears access_token from localStorage', async () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('user', JSON.stringify({ id: '1', email: 'a@b.com' }))

    renderWithAuth(<LogoutConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('a@b.com')
    })

    await act(async () => {
      screen.getByTestId('logout-btn').click()
    })

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
  })

  test('logout navigates to /login', async () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('user', JSON.stringify({ id: '1', email: 'a@b.com' }))

    renderWithAuth(<LogoutConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('a@b.com')
    })

    await act(async () => {
      screen.getByTestId('logout-btn').click()
    })

    expect(mockPush).toHaveBeenCalledWith('/login')
  })
})
