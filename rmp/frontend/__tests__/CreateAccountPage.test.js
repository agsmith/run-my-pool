import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CreateAccountPage from '../pages/create-account'

const mockPush = jest.fn()

jest.mock('next/router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

jest.mock('../styles/globalStyles', () => ({
  baseStyles: { authPageContainer: {}, authCard: {} },
}))

describe('CreateAccountPage', () => {
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
})
