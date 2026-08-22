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
      entitlement: { plan: 'pro', status: 'active', included_entries: 150, max_pools: 3, unlimited_entries: false },
      used_entries: 12,
      pools_created: 2,
      plan_year_start: '2026-03-01',
      plan_year_end: '2027-02-28',
      orders: [{ id: 'order-1', plan: 'pro', status: 'paid', amount_total: 7900, currency: 'usd', paid_at: '2026-08-12T12:00:00' }],
    }));
    render(<Profile />);

    expect(await screen.findAllByText('Pro')).toHaveLength(2);
    expect(screen.getByText('$79.00')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('12 / 150')).toBeInTheDocument();
    expect(screen.getByText('2 / 3')).toBeInTheDocument();
    expect(screen.getByText(/March 1, 2026 through February 28, 2027/i)).toBeInTheDocument();
    expect(screen.getByText(/Deleted or concluded pools still count/i)).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith('/billing/overview?season=2026', expect.objectContaining({ credentials: 'include' }));
    expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('billing_overview_view', { page: 'profile' });
  });

  test('offers a return to setup while paid pool capacity remains unused', async () => {
    global.fetch = jest.fn(() => response({
      season: 2026,
      entitlement: { plan: 'pro', status: 'active', included_entries: 150, max_pools: 3, unlimited_entries: false },
      used_entries: 0,
      used_pools: 0,
      pools_created: 0,
      plan_year_start: '2026-03-01',
      plan_year_end: '2027-02-28',
      can_create_pool: true,
      available_pool_slots: 3,
      orders: [],
    }));

    render(<Profile />);

    expect(await screen.findByRole('heading', { name: /your purchased pool is ready/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /create your pool/i })).toHaveAttribute('href', '/create-pool?source=splash');
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

  test('starts a difference-priced upgrade from the billing page', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() => response({
        season: 2026,
        entitlement: { plan: 'commissioner', status: 'active', included_entries: 50, max_pools: 1, unlimited_entries: false },
        used_entries: 20,
        orders: [],
      }))
      .mockImplementationOnce(() => response({ detail: 'Test checkout stop' }, false));
    const user = userEvent.setup();
    render(<Profile />);

    await user.click(await screen.findByRole('button', { name: 'Upgrade to Pro — $40' }));

    expect(global.fetch).toHaveBeenLastCalledWith('/billing/checkout-session', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ plan: 'pro', season: 2026, order_type: 'plan', quantity: 1 }),
    }));
  });

  test('buys multiple Club entry blocks', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() => response({
        season: 2026,
        entitlement: { plan: 'club', status: 'active', included_entries: 500, entry_block_count: 0, max_pools: 5, unlimited_entries: false },
        used_entries: 490,
        orders: [],
      }))
      .mockImplementationOnce(() => response({ detail: 'Test checkout stop' }, false));
    const user = userEvent.setup();
    render(<Profile />);

    expect(await screen.findByRole('button', { name: 'Upgrade to Club Unlimited — $120' })).toBeInTheDocument();
    await user.selectOptions(await screen.findByLabelText('Additional 100-entry blocks'), '3');
    await user.click(screen.getByRole('button', { name: 'Add 300 entries — $75' }));

    expect(global.fetch).toHaveBeenLastCalledWith('/billing/checkout-session', expect.objectContaining({
      body: JSON.stringify({ plan: undefined, season: 2026, order_type: 'entry_blocks', quantity: 3 }),
    }));
  });
});
