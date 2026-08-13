import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
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
});
