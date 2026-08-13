import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Profile from '../pages/profile';

const mockLogout = jest.fn();
const mockTrackLifecycleEvent = jest.fn();
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'commish@example.com' }, logout: mockLogout }),
}));
jest.mock('../lib/lifecycleAnalytics', () => ({
  trackLifecycleEvent: (...args) => mockTrackLifecycleEvent(...args),
}));

const response = (data, ok = true) => Promise.resolve({
  ok,
  json: () => Promise.resolve(data),
});

describe('profile billing overview', () => {
  beforeEach(() => {
    mockLogout.mockReset();
    mockTrackLifecycleEvent.mockReset();
    localStorage.setItem('access_token', 'token');
    process.env.NEXT_PUBLIC_API_URL = '';
    process.env.NEXT_PUBLIC_NFL_SEASON = '2026';
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('shows the current commissioner plan and payment history', async () => {
    global.fetch = jest.fn(() => response({
      season: 2026,
      entitlement: { plan: 'pro', status: 'active', included_entries: 150, max_pools: 1, unlimited_entries: false },
      orders: [{ id: 'order-1', plan: 'pro', status: 'paid', amount_total: 7900, currency: 'usd', paid_at: '2026-08-12T12:00:00' }],
    }));
    render(<Profile />);

    expect(await screen.findAllByText('Pro')).toHaveLength(2);
    expect(screen.getByText('$79.00')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith('/billing/overview?season=2026', expect.objectContaining({ credentials: 'include' }));
    expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('billing_overview_view', { page: 'profile' });
  });

  test('explains free access when there are no payments', async () => {
    global.fetch = jest.fn(() => response({ season: 2026, entitlement: null, orders: [] }));
    render(<Profile />);

    expect(await screen.findByText('Free')).toBeInTheDocument();
    expect(screen.getByText(/members always participate free/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View plans' })).toHaveAttribute('href', '/pricing');
  });

  test('keeps billing support available when loading fails', async () => {
    global.fetch = jest.fn(() => response({}, false));
    render(<Profile />);

    expect(await screen.findByText(/unable to load billing details/i)).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /support/i })[0]).toHaveAttribute('href', '/support');
  });

  test('logs out from the account header', async () => {
    global.fetch = jest.fn(() => response({ season: 2026, entitlement: null, orders: [] }));
    const user = userEvent.setup();
    render(<Profile />);

    await user.click(screen.getByRole('button', { name: 'Logout' }));
    expect(mockLogout).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  });
});
