import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CreateAccountPage from '../pages/create-account'

const mockPush = jest.fn()
let mockQuery = {}

jest.mock('next/router', () => ({
  useRouter: () => ({ push: mockPush, query: mockQuery }),
}))

jest.mock('../styles/globalStyles', () => ({
  baseStyles: { authPageContainer: {}, authCard: {} },
}))

describe('CreateAccountPage', () => {
  beforeEach(() => {
    mockPush.mockClear()
    mockQuery = {}
  })

  test('uses the Broadcast Night product brand without an emoji', () => {
    const { container } = render(<CreateAccountPage />)
    expect(screen.getByRole('heading', { name: /run my pool/i })).toBeInTheDocument()
    expect(container.querySelector('.product-football-mark')).toBeInTheDocument()
    expect(container).not.toHaveTextContent('🏈')
  })

  test('shows and hides both password fields independently', async () => {
    const user = userEvent.setup()
    render(<CreateAccountPage />)
    const password = screen.getByPlaceholderText(/^enter your password$/i)
    const confirmation = screen.getByPlaceholderText(/confirm your password/i)

    await user.click(screen.getByRole('button', { name: /show new account password/i }))
    expect(password).toHaveAttribute('type', 'text')
    expect(confirmation).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: /show password confirmation/i }))
    expect(confirmation).toHaveAttribute('type', 'text')
  })

  test('links existing users back to login', () => {
    render(<CreateAccountPage />)
    expect(screen.getByRole('link', { name: /already have an account/i })).toHaveAttribute('href', '/login')
  })

  test('shows the API reason when account creation is rejected', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'Email already registered' }),
    })
    const user = userEvent.setup()
    render(<CreateAccountPage />)

    await user.type(screen.getByPlaceholderText(/enter your email/i), 'Existing@Example.com')
    await user.type(screen.getByPlaceholderText(/^enter your password$/i), 'ValidPass1!')
    await user.type(screen.getByPlaceholderText(/confirm your password/i), 'ValidPass1!')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    expect(await screen.findByText(/your account may have been created successfully/i)).toBeInTheDocument()
    expect(JSON.parse(global.fetch.mock.calls[0][1].body).email).toBe('existing@example.com')
  })

  test('keeps confirmed success visible if client-side navigation fails', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true })
    mockPush.mockRejectedValueOnce(new Error('Safari navigation interrupted'))
    const user = userEvent.setup()
    render(<CreateAccountPage />)

    await user.type(screen.getByPlaceholderText(/enter your email/i), 'new@example.com')
    await user.type(screen.getByPlaceholderText(/^enter your password$/i), 'ValidPass1!')
    await user.type(screen.getByPlaceholderText(/confirm your password/i), 'ValidPass1!')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    expect(await screen.findByText(/account created successfully/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /continue to sign in/i })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('button', { name: 'Account Created' })).toBeDisabled()
    expect(screen.queryByText(/account creation failed/i)).not.toBeInTheDocument()
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  test('continues a splash-page pool creation after registration and login', async () => {
    mockQuery = { intent: 'create-pool' }
    global.fetch = jest.fn().mockResolvedValue({ ok: true })
    const user = userEvent.setup()
    render(<CreateAccountPage />)

    await user.type(screen.getByPlaceholderText(/enter your email/i), 'new@example.com')
    await user.type(screen.getByPlaceholderText(/^enter your password$/i), 'ValidPass1!')
    await user.type(screen.getByPlaceholderText(/confirm your password/i), 'ValidPass1!')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining(
      `next=${encodeURIComponent('/create-pool?source=splash')}`,
    ))
  })
})
