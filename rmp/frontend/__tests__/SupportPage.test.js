import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SupportPage from '../pages/support';

const mockTrackLifecycleEvent = jest.fn();
jest.mock('../lib/lifecycleAnalytics', () => ({
  trackLifecycleEvent: (...args) => mockTrackLifecycleEvent(...args),
}));

describe('support hub', () => {
  beforeEach(() => mockTrackLifecycleEvent.mockClear());

  test('offers public self-service paths for each support category', () => {
    render(<SupportPage />);

    expect(screen.getByRole('heading', { name: /how can we help/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Reset your password' })).toHaveAttribute('href', '/forgot-password');
    expect(screen.getByRole('link', { name: 'Browse pools' })).toHaveAttribute('href', '/leagues');
    expect(screen.getByRole('link', { name: 'Review plans' })).toHaveAttribute('href', '/pricing');
    expect(screen.getByRole('link', { name: 'Install or refresh the app' })).toHaveAttribute('href', '/install');
    expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('support_hub_view', { page: 'support' });
  });

  test('categorizes support email without including sensitive customer data', async () => {
    const user = userEvent.setup();
    render(<SupportPage />);
    const billingCard = screen.getByRole('heading', { name: 'Billing' }).closest('article');
    const email = billingCard.querySelector('a[href^="mailto:"]');

    expect(email).toHaveAttribute('href', expect.stringContaining('subject=Run%20My%20Pool%20billing%20support'));
    expect(email.getAttribute('href')).not.toMatch(/password=|card=/i);
    email.addEventListener('click', (event) => event.preventDefault());
    await user.click(email);
    expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('support_contact_clicked', { page: 'support' });
  });

  test('shows troubleshooting details and safety guidance', () => {
    render(<SupportPage />);

    expect(screen.getByText(/exact error shown/i)).toBeInTheDocument();
    expect(screen.getByText(/never send a password or payment-card number/i)).toBeInTheDocument();
    expect(screen.getByText(/you do not need to be signed in/i)).toBeInTheDocument();
  });
});
