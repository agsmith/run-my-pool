import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VerifyEmailPage from '../pages/verify-email';

let query = {};
jest.mock('next/router', () => ({ useRouter: () => ({ query }) }));
jest.mock('../styles/globalStyles', () => ({ baseStyles: { authPageContainer: {}, authCard: {} } }));

describe('VerifyEmailPage', () => {
  beforeEach(() => { query = {}; global.fetch = jest.fn(); });

  test('consumes a verification token and continues to the requested page through login', async () => {
    query = { token: 'a'.repeat(43), next: '/leagues?invite=pool-1' };
    fetch.mockResolvedValue({ ok: true, json: async () => ({ message: 'Email verified successfully. You can now sign in.' }) });
    render(<VerifyEmailPage />);

    expect(await screen.findByText(/email verified successfully/i)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/auth/verify-email', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ token: 'a'.repeat(43) }),
    }));
    expect(screen.getByRole('link', { name: /continue to sign in/i })).toHaveAttribute(
      'href',
      `/login?message=${encodeURIComponent('Email verified successfully. Please sign in.')}&next=${encodeURIComponent('/leagues?invite=pool-1')}`,
    );
  });

  test('requests a replacement without revealing whether an account exists', async () => {
    query = { email: 'member@example.com' };
    fetch.mockResolvedValue({ ok: true, json: async () => ({ message: 'If that account still needs verification, a new email will arrive shortly.' }) });
    const user = userEvent.setup();
    render(<VerifyEmailPage />);

    await waitFor(() => expect(screen.getByRole('textbox', { name: /email address/i })).toHaveValue('member@example.com'));
    await user.click(screen.getByRole('button', { name: /resend verification email/i }));
    expect(await screen.findByText(/if that account still needs verification/i)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/auth/resend-verification', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ email: 'member@example.com' }),
    }));
  });
});
