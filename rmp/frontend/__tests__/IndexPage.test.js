import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import IndexPage from '../pages/index'

const mockTrackLifecycleEvent = jest.fn()
jest.mock('../lib/lifecycleAnalytics', () => ({
  trackLifecycleEvent: (...args) => mockTrackLifecycleEvent(...args),
}))

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
  mockTrackLifecycleEvent.mockClear()
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

  test('puts a dedicated pricing link in the hero on desktop and mobile', () => {
    render(<IndexPage />)

    expect(screen.getByRole('link', { name: 'View Pricing' })).toHaveAttribute('href', '/pricing')
  })

  test('explains the complete commissioner and member workflow', () => {
    render(<IndexPage />)

    expect(screen.getByRole('heading', { name: 'BUILD YOUR POOL' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'BRING IN YOUR CREW' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'MAKE THE PICKS' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'FOLLOW THE RESULTS' })).toBeInTheDocument()
    expect(screen.getByText(/at lock, surviving-entry picks are revealed/i)).toBeInTheDocument()
    expect(screen.getByText(/identify autopicks, manage locks and members/i)).toBeInTheDocument()
    expect(screen.getByText(/see your remaining entries and weekly progress/i)).toBeInTheDocument()
  })

  test('records a privacy-safe landing page view', () => {
    render(<IndexPage />)

    expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('landing_view', {
      page: 'home',
      source: 'direct',
    })
  })

  test('explains all supported pool formats before signup', () => {
    render(<IndexPage />)

    expect(screen.getByRole('heading', { name: /last entry standing/i })).toBeInTheDocument()
    expect(screen.getByText(/one pick per surviving entry/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /most wins takes it/i })).toBeInTheDocument()
    expect(screen.getByText(/one point for every winner/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /own the board/i })).toBeInTheDocument()
    expect(screen.getByText(/100 numbered squares/i)).toBeInTheDocument()
    expect(screen.getByText('Quarter, halftime, and final winners')).toBeInTheDocument()
  })

  test('answers essential pre-purchase questions and links to support', () => {
    render(<IndexPage />)

    expect(screen.getByText('When do weekly picks lock?')).toBeInTheDocument()
    expect(screen.getByText('Can a pool be private?')).toBeInTheDocument()
    expect(screen.getByText('What happens if someone forgets to pick?')).toBeInTheDocument()
    expect(screen.getByText('Do members have to pay?')).toBeInTheDocument()
    expect(screen.getByText('Does Run My Pool handle prize money?')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /contact support/i })).toEqual(
      expect.arrayContaining([expect.objectContaining({ href: 'http://localhost/support' })]),
    )
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

  test('explains the complete pool-management feature set', () => {
    render(<IndexPage />)

    expect(screen.getByRole('heading', { name: /configurable pool setup/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /weekly automation/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /member experience/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /commissioner controls/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /transparent competition/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /affordable growth/i })).toBeInTheDocument()
    expect(screen.getByText(/all surviving picks revealed at weekly lock/i)).toBeInTheDocument()
    expect(screen.getByText(/pool-scoped users, entries, picks, and roles/i)).toBeInTheDocument()
    expect(screen.getByText(/club expansion blocks and an unlimited option/i)).toBeInTheDocument()
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
