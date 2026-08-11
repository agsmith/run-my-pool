import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ForgotPassword from '../pages/forgot-password';

process.env.NEXT_PUBLIC_API_URL = '';

describe('forgot password', () => {
  afterEach(() => jest.restoreAllMocks());

  test('rejects malformed email without contacting the API', async () => {
    global.fetch = jest.fn();
    const user = userEvent.setup();
    render(<ForgotPassword />);

    await user.type(screen.getByPlaceholderText('Enter your email address'), 'not-an-email');
    fireEvent.submit(screen.getByRole('button', { name: 'Send Reset Link' }).closest('form'));

    expect(screen.getByText('Please enter a valid email address.')).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  test('submits a valid address without revealing whether the account exists', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<ForgotPassword />);

    await user.type(screen.getByPlaceholderText('Enter your email address'), 'player@example.com');
    await user.click(screen.getByRole('button', { name: 'Send Reset Link' }));

    expect(await screen.findByText(/if your email is registered/i)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/auth/forgot-password', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ email: 'player@example.com' }),
    }));
  });

  test('shows a recoverable error when delivery fails', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false });
    const user = userEvent.setup();
    render(<ForgotPassword />);

    await user.type(screen.getByPlaceholderText('Enter your email address'), 'player@example.com');
    await user.click(screen.getByRole('button', { name: 'Send Reset Link' }));

    expect(await screen.findByText('Failed to send reset email.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send Reset Link' })).toBeEnabled();
  });
});
