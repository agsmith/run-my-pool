import '@testing-library/jest-dom'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginPage from '../pages/login'

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
let mockQuery = {}

jest.mock('next/router', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
    query: mockQuery,
    pathname: '/login',
  }),
}))

// ---------------------------------------------------------------------------
// globalStyles mock — the page and ResponsiveComponents import from this;
// returning plain objects avoids needing a full style implementation.
// ---------------------------------------------------------------------------
jest.mock('../styles/globalStyles', () => ({
  baseStyles: {},
  createHoverHandlers: () => ({}),
  hoverEffects: {},
  createFocusHandlers: () => ({}),
  mobileStyles: {},
  getResponsiveStyle: () => ({}),
  touchStyles: {},
}))

beforeEach(() => {
  mockPush.mockClear()
  mockQuery = {}
  // Default: not loading, login succeeds
  useAuth.mockReturnValue({
    login: jest.fn().mockResolvedValue(undefined),
    user: null,
    loading: false,
  })
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Valid credentials that pass both client-side validators. */
const VALID_EMAIL = 'user@example.com'
const VALID_PASSWORD = 'Secure1!'

function renderLogin() {
  return render(<LoginPage />)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('LoginPage', () => {
  test('uses the product brand without a football emoji', () => {
    const { container } = renderLogin()
    expect(screen.getByRole('heading', { name: /run my pool/i })).toBeInTheDocument()
    expect(screen.getByText(/sign in to your account/i)).toBeInTheDocument()
    expect(container).not.toHaveTextContent('🏈')
    expect(screen.getByRole('img', { name: /run my pool/i })).toHaveAttribute('src', '/brand/promotional/rmp-alt-compact-dark.png')
  })

  test('renders an email input field', () => {
    renderLogin()
    expect(screen.getByPlaceholderText(/enter your email/i)).toBeInTheDocument()
  })

  test('renders a password input field', () => {
    renderLogin()
    expect(screen.getByPlaceholderText(/enter your password/i)).toBeInTheDocument()
  })

  test('can show and hide the login password', async () => {
    const user = userEvent.setup()
    renderLogin()
    const password = screen.getByPlaceholderText(/enter your password/i)

    expect(password).toHaveAttribute('type', 'password')
    await user.click(screen.getByRole('button', { name: /show login password/i }))
    expect(password).toHaveAttribute('type', 'text')
    await user.click(screen.getByRole('button', { name: /hide login password/i }))
    expect(password).toHaveAttribute('type', 'password')
  })

  test('renders the Sign In submit button', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  test('shows a link to create a new account', () => {
    renderLogin()
    const link = screen.getByRole('link', { name: /create new account/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/create-account')
  })

  test('shows and preserves the package being continued after sign in', () => {
    mockQuery = { next: '/pricing?checkout=pro' }
    renderLogin()

    expect(screen.getByLabelText('Selected package')).toHaveTextContent('Pro')
    expect(screen.getByRole('link', { name: /create new account/i })).toHaveAttribute('href', '/create-account?plan=pro')
  })

  test('continues a selected Free package to pool setup', async () => {
    const mockLogin = jest.fn().mockResolvedValue(undefined)
    useAuth.mockReturnValue({ login: mockLogin, user: null, loading: false })
    mockQuery = { next: '/create-pool?source=splash' }
    const user = userEvent.setup()
    renderLogin()

    expect(screen.getByLabelText('Selected package')).toHaveTextContent('Free')
    await user.type(screen.getByPlaceholderText(/enter your email/i), VALID_EMAIL)
    await user.type(screen.getByPlaceholderText(/enter your password/i), VALID_PASSWORD)
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(mockLogin).toHaveBeenCalledWith(VALID_EMAIL, VALID_PASSWORD, '/create-pool?source=splash')
  })

  test('preserves a pool invitation when a new user needs an account', () => {
    mockQuery = { next: '/leagues?invite=pool-1' }
    renderLogin()

    expect(screen.getByRole('link', { name: /create new account/i })).toHaveAttribute(
      'href',
      `/create-account?next=${encodeURIComponent('/leagues?invite=pool-1')}`,
    )
  })

  test('shows a link to the forgot-password page', () => {
    renderLogin()
    const link = screen.getByRole('link', { name: /forgot your password/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/forgot-password')
  })

  test('calls login with the entered email and password on submit', async () => {
    const mockLogin = jest.fn().mockResolvedValue(undefined)
    useAuth.mockReturnValue({ login: mockLogin, user: null, loading: false })

    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/enter your email/i), VALID_EMAIL)
    await user.type(screen.getByPlaceholderText(/enter your password/i), VALID_PASSWORD)
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith(VALID_EMAIL, VALID_PASSWORD)
    })
  })

  test('does not call login when email format is invalid', async () => {
    const mockLogin = jest.fn()
    useAuth.mockReturnValue({ login: mockLogin, user: null, loading: false })

    const user = userEvent.setup()
    renderLogin()

    // Use type="text" workaround: set value then submit via fireEvent to bypass
    // the browser's native email validation and reach our JS validator.
    const emailInput = screen.getByPlaceholderText(/enter your email/i)
    const passwordInput = screen.getByPlaceholderText(/enter your password/i)

    await user.type(passwordInput, VALID_PASSWORD)
    // Override the input value directly so the native email constraint doesn't block submit
    fireEvent.change(emailInput, { target: { value: 'notanemail' } })
    fireEvent.submit(emailInput.closest('form'))

    expect(mockLogin).not.toHaveBeenCalled()
  })

  test('shows a validation error message when email format is invalid', async () => {
    const user = userEvent.setup()
    renderLogin()

    const emailInput = screen.getByPlaceholderText(/enter your email/i)
    const passwordInput = screen.getByPlaceholderText(/enter your password/i)

    await user.type(passwordInput, VALID_PASSWORD)
    fireEvent.change(emailInput, { target: { value: 'notanemail' } })
    fireEvent.submit(emailInput.closest('form'))

    expect(
      screen.getByText(/please enter a valid email address/i)
    ).toBeInTheDocument()
  })

  test('allows an existing legacy password to reach authentication', async () => {
    const mockLogin = jest.fn()
    useAuth.mockReturnValue({ login: mockLogin, user: null, loading: false })

    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/enter your email/i), VALID_EMAIL)
    // "abc" — too short and missing uppercase/number/special
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'abc')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(mockLogin).toHaveBeenCalledWith(VALID_EMAIL, 'abc')
  })

  test('shows the new-password policy as login subtext', () => {
    renderLogin()

    expect(screen.getByText(/new passwords require 8\+ characters/i)).toBeInTheDocument()
  })

  test('displays error message when login throws Invalid credentials', async () => {
    const mockLogin = jest.fn().mockRejectedValue(new Error('Invalid credentials'))
    useAuth.mockReturnValue({ login: mockLogin, user: null, loading: false })

    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/enter your email/i), VALID_EMAIL)
    await user.type(screen.getByPlaceholderText(/enter your password/i), VALID_PASSWORD)
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })

  test('offers verification help when the API blocks an unverified account', async () => {
    const verificationError = Object.assign(new Error('Verify your email before signing in.'), { code: 'email_not_verified' })
    const mockLogin = jest.fn().mockRejectedValue(verificationError)
    useAuth.mockReturnValue({ login: mockLogin, user: null, loading: false })
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/enter your email/i), 'New@Example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), VALID_PASSWORD)
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('link', { name: /resend verification email/i })).toHaveAttribute(
      'href', '/verify-email?email=new%40example.com',
    )
  })

  test('shows "Signing in..." text on the button while loading is true', () => {
    useAuth.mockReturnValue({ login: jest.fn(), user: null, loading: true })

    renderLogin()

    expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument()
  })

  test('disables the submit button while loading is true', () => {
    useAuth.mockReturnValue({ login: jest.fn(), user: null, loading: true })

    renderLogin()

    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
  })
})
