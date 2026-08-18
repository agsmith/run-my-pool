import '@testing-library/jest-dom';
import { act, render, screen, waitFor } from '@testing-library/react';
import BillingSuccessPage from '../pages/billing/success';

const mockTrackLifecycleEvent = jest.fn();
jest.mock('../lib/lifecycleAnalytics', () => ({
  trackLifecycleEvent: (...args) => mockTrackLifecycleEvent(...args),
}));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);
jest.mock('next/router', () => ({
  useRouter: () => ({ isReady: true, query: { session_id: 'cs_paid' } }),
}));

describe('BillingSuccessPage', () => {
  beforeEach(() => {
    mockTrackLifecycleEvent.mockClear();
    window.localStorage.setItem('access_token', 'token');
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 'order-1',
        plan: 'pro',
        season: 2026,
        status: 'paid',
        amount_total: 7900,
        currency: 'usd',
      }),
    });
  });

  test('sends a confirmed customer directly into pool creation', async () => {
    render(<BillingSuccessPage />);

    expect(await screen.findByRole('heading', { name: /payment confirmed/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /create your pool/i })).toHaveAttribute('href', '/create-pool?source=splash');
    expect(screen.getByRole('link', { name: /go to dashboard/i })).toHaveAttribute('href', '/dashboard');
    await waitFor(() => expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('payment_confirmed', {
      page: 'billing_success',
      plan: 'pro',
      source: 'pricing',
    }));
  });

  test('confirms Club capacity without presenting it as a new plan', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 'order-blocks',
        plan: 'club-entry-block',
        order_type: 'entry_blocks',
        quantity: 3,
        season: 2026,
        status: 'paid',
        amount_total: 7500,
        currency: 'usd',
      }),
    });

    render(<BillingSuccessPage />);

    expect(await screen.findByText(/capacity increased by/i)).toHaveTextContent('300 entries');
    expect(screen.getByRole('link', { name: /return to billing/i })).toHaveAttribute('href', '/profile');
    expect(screen.queryByRole('link', { name: /create your pool/i })).not.toBeInTheDocument();
    await waitFor(() => expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('payment_confirmed', {
      page: 'billing_success',
      plan: 'club',
      source: 'billing',
    }));
  });

  test('I05 polls safely from pending to paid and records confirmation once', async () => {
    jest.useFakeTimers();
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'order-poll', plan: 'pro', season: 2026, status: 'pending' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'order-poll', plan: 'pro', season: 2026, status: 'paid', amount_total: 7900, currency: 'usd' }) });

    render(<BillingSuccessPage />);
    expect(await screen.findByRole('heading', { name: /confirming payment/i })).toBeInTheDocument();

    await act(async () => { jest.advanceTimersByTime(1500); });

    expect(await screen.findByRole('heading', { name: /payment confirmed/i })).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(mockTrackLifecycleEvent).toHaveBeenCalledTimes(1);
    jest.useRealTimers();
  });

  test('J02 does not reveal another account checkout session', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({ detail: 'Checkout session not found' }) });
    render(<BillingSuccessPage />);
    expect(await screen.findByText('Unable to confirm this payment.')).toBeInTheDocument();
    expect(screen.queryByText(/\$79/)).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /create your pool/i })).not.toBeInTheDocument();
  });
});
