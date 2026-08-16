import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import PricingPage from '../pages/pricing';
import userEvent from '@testing-library/user-event';

const mockTrackLifecycleEvent = jest.fn();
jest.mock('../lib/lifecycleAnalytics', () => ({
  trackLifecycleEvent: (...args) => mockTrackLifecycleEvent(...args),
}));

const mockPush = jest.fn();
const mockRouter = { query: {}, isReady: true, push: mockPush };
let mockAuth = { user: null, token: null };
jest.mock('next/router', () => ({ useRouter: () => mockRouter }));
jest.mock('../context/AuthContext', () => ({ useAuth: () => mockAuth }));

describe('PricingPage', () => {
  beforeEach(() => {
    mockTrackLifecycleEvent.mockClear();
    mockPush.mockClear();
    mockRouter.query = {};
    mockAuth = { user: null, token: null };
  });

  test('records the pricing view and selected package', async () => {
    const user = userEvent.setup();
    render(<PricingPage />);

    expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('pricing_view', { page: 'pricing', source: 'homepage' });
    await user.click(screen.getByRole('link', { name: /choose pro/i }));
    expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('plan_selected', {
      page: 'pricing',
      plan: 'pro',
      source: 'pricing',
    });
  });

  test('shows the recommended plans and prices', () => {
    render(<PricingPage />);
    expect(screen.getByRole('heading', { name: 'Free' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Squares Plus' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Commish' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Pro' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Club' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Club Unlimited' })).toBeInTheDocument();
    expect(screen.getByText('$10')).toBeInTheDocument();
    expect(screen.getByText('$39')).toBeInTheDocument();
    expect(screen.getByText('$79')).toBeInTheDocument();
    expect(screen.getByText('$129')).toBeInTheDocument();
    expect(screen.getByText('$249')).toBeInTheDocument();
    expect(screen.getByText('1 Squares board per season')).toBeInTheDocument();
    expect(screen.getByText('Up to 25 self-service Squares reservations')).toBeInTheDocument();
    expect(screen.getByText('1 full Squares board per season')).toBeInTheDocument();
    expect(screen.getByText('All 100 self-service reservations')).toBeInTheDocument();
    expect(screen.getByText('Full 100-block Squares board')).toBeInTheDocument();
    expect(screen.getByText('Admin assignment of any numbered block')).toBeInTheDocument();
    expect(screen.getByText('Fixed-dollar or per-reserved-block pots')).toBeInTheDocument();
    expect(screen.getByText(/start with up to ten Survivor\/Pick ’Em entries or one 25-reservation Squares board/i)).toBeInTheDocument();
  });

  test('makes the software-only payment model explicit', () => {
    render(<PricingPage />);
    expect(screen.getByText(/never takes a percentage/i)).toBeInTheDocument();
    expect(screen.getByText(/does not collect stakes or distribute winnings/i)).toBeInTheDocument();
  });

  test('links each plan to account creation', () => {
    render(<PricingPage />);
    expect(screen.getAllByRole('link', { name: /start free/i }).some((link) => link.getAttribute('href') === '/create-account?plan=free')).toBe(true);
    expect(screen.getByRole('link', { name: /choose commissioner/i })).toHaveAttribute('href', '/create-account?plan=commissioner');
    expect(screen.getByRole('link', { name: /choose squares plus/i })).toHaveAttribute('href', '/create-account?plan=squares-plus');
    expect(screen.getByRole('link', { name: /choose pro/i })).toHaveAttribute('href', '/create-account?plan=pro');
    expect(screen.getByRole('link', { name: /choose club/i })).toHaveAttribute('href', '/create-account?plan=club');
    expect(screen.getByRole('link', { name: /go unlimited/i })).toHaveAttribute('href', '/create-account?plan=club-unlimited');
  });

  test('takes a signed-in Free customer directly to pool setup', () => {
    mockAuth = { user: { id: 'user-1' }, token: 'token' };
    render(<PricingPage />);

    expect(screen.getAllByRole('link', { name: /start free/i }).every((link) => link.getAttribute('href') === '/create-pool?source=splash')).toBe(true);
  });

  test('keeps a signed-in customer in the buy flow and shows the paid package first', async () => {
    const user = userEvent.setup();
    mockAuth = { user: { id: 'user-1' }, token: 'token' };
    render(<PricingPage />);

    await user.click(screen.getByRole('link', { name: /choose pro/i }));

    expect(mockPush).toHaveBeenCalledWith('/pricing?checkout=pro');
  });

  test('starts secure checkout only after the returning user confirms the package', async () => {
    const user = userEvent.setup();
    mockRouter.query = { checkout: 'pro' };
    mockAuth = { user: { id: 'user-1' }, token: 'token' };
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'Test checkout stop' }),
    });
    render(<PricingPage />);

    const selection = screen.getByLabelText('Selected package');
    expect(selection).toHaveTextContent('Pro');
    expect(selection).toHaveTextContent('$79');
    expect(global.fetch).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: /continue to secure checkout/i }));

    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/billing/checkout-session'), expect.objectContaining({
      method: 'POST',
      body: expect.stringContaining('"plan":"pro"'),
    }));
  });

  test('preserves the package when a returning customer still needs to sign in', () => {
    mockRouter.query = { checkout: 'club' };
    render(<PricingPage />);

    expect(screen.getByLabelText('Selected package')).toHaveTextContent('Club');
    expect(screen.getByRole('link', { name: /sign in to continue/i })).toHaveAttribute(
      'href',
      `/login?next=${encodeURIComponent('/pricing?checkout=club')}`,
    );
  });

  test('identifies the package when checkout is canceled', () => {
    mockRouter.query = { checkout: 'cancelled', plan: 'pro' };
    render(<PricingPage />);

    expect(screen.getByText(/Pro checkout was canceled.*No payment was taken/i)).toBeInTheDocument();
  });

  test('positions Club around multiple pools and historical access', () => {
    render(<PricingPage />);
    const clubCard = screen.getByRole('heading', { name: 'Club' }).closest('article');
    expect(clubCard).toHaveTextContent('Up to 5 active pools');
    expect(clubCard).toHaveTextContent('Full historical access');
    expect(clubCard).toHaveTextContent('$129');
    expect(clubCard).toHaveTextContent('per season');
    expect(clubCard).toHaveTextContent('$25 per additional 100 entries');
  });

  test('makes unlimited the clear choice for large pools', () => {
    render(<PricingPage />);
    const unlimitedCard = screen.getByRole('heading', { name: 'Club Unlimited' }).closest('article');
    expect(unlimitedCard).toHaveTextContent('$249');
    expect(unlimitedCard).toHaveTextContent('Unlimited entries');
    expect(unlimitedCard).toHaveTextContent('Unlimited active pools');
    expect(unlimitedCard).toHaveTextContent('No usage charges');
    expect(screen.getByText(/upgrade to Club Unlimited for the \$120 difference/i)).toBeInTheDocument();
    expect(screen.getByText(/select it initially or upgrade from Club later/i)).toBeInTheDocument();
  });

  test('links to billing and account support', () => {
    render(<PricingPage />);
    expect(screen.getByRole('link', { name: /billing and account support/i })).toHaveAttribute('href', '/support');
  });
});
