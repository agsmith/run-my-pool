import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PoolInvitationPage from '../pages/join/[id]';

process.env.NEXT_PUBLIC_API_URL = '';

const mockPush = jest.fn();
let currentUser = null;

jest.mock('next/router', () => ({
  useRouter: () => ({
    isReady: true,
    query: { id: 'pool-1' },
    push: mockPush,
  }),
}));

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: currentUser, loading: false }),
}));

function response(data, ok = true) {
  return Promise.resolve({ ok, json: () => Promise.resolve(data) });
}

describe('Pool invitation landing page', () => {
  beforeEach(() => {
    currentUser = null;
    mockPush.mockReset();
    global.fetch = jest.fn(() => response({
      id: 'pool-1',
      name: 'Office Survivor',
      description: 'Last entry standing wins.',
      is_private: true,
    }));
  });

  test('shows the scanned pool without requiring authentication', async () => {
    render(<PoolInvitationPage />);

    expect(await screen.findByRole('heading', { name: 'Office Survivor' })).toBeInTheDocument();
    expect(screen.getByText('Private pool')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/pools/invite/pool-1', { cache: 'no-store' });
  });

  test('requires login to join and preserves the pool invitation', async () => {
    const user = userEvent.setup();
    render(<PoolInvitationPage />);
    await screen.findByRole('heading', { name: 'Office Survivor' });

    await user.click(screen.getByRole('button', { name: 'Log in to join pool' }));

    expect(mockPush).toHaveBeenCalledWith(
      `/login?next=${encodeURIComponent('/leagues?invite=pool-1')}`,
    );
    expect(screen.getByRole('link', { name: /need an account/i })).toHaveAttribute(
      'href',
      `/create-account?next=${encodeURIComponent('/leagues?invite=pool-1')}`,
    );
  });

  test('sends an authenticated user directly to the pool join flow', async () => {
    currentUser = { id: 'user-1' };
    const user = userEvent.setup();
    render(<PoolInvitationPage />);
    await screen.findByRole('heading', { name: 'Office Survivor' });

    await user.click(screen.getByRole('button', { name: 'Continue to join pool' }));

    expect(mockPush).toHaveBeenCalledWith('/leagues?invite=pool-1');
  });

  test('does not reveal a missing or invalid invitation', async () => {
    global.fetch = jest.fn(() => response({ detail: 'Pool invitation not found' }, false));
    render(<PoolInvitationPage />);

    expect(await screen.findByRole('heading', { name: 'Invitation unavailable' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Pool invitation not found');
    await waitFor(() => expect(screen.queryByRole('button', { name: /join pool/i })).not.toBeInTheDocument());
  });
});
