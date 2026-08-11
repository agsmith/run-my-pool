import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import LeaguePasswordViewer from '../components/LeaguePasswordViewer';

describe('LeaguePasswordViewer', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token');
    global.fetch = jest.fn();
  });

  afterEach(() => {
    localStorage.clear();
    jest.restoreAllMocks();
  });

  test('reveals and hides the current league password', async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ available: true, password: 'sideline8' }),
    });
    render(<LeaguePasswordViewer poolId="pool-1" isPrivate />);

    fireEvent.click(screen.getByRole('button', { name: 'Show password' }));

    await waitFor(() => expect(screen.getByLabelText('Current password')).toHaveValue('sideline8'));
    expect(screen.getByLabelText('Current password')).toHaveAttribute('type', 'text');
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/pools/pool-1/join-password'),
      expect.objectContaining({ cache: 'no-store' }),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Hide password' }));
    expect(screen.getByLabelText('Current password')).toHaveAttribute('type', 'password');
  });

  test('explains why an existing hashed password is unavailable', async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ available: false, password: null }),
    });
    render(<LeaguePasswordViewer poolId="legacy-pool" isPrivate />);

    fireEvent.click(screen.getByRole('button', { name: 'Show password' }));

    expect(await screen.findByText(/set a new password to make it viewable/i)).toBeInTheDocument();
  });
});
