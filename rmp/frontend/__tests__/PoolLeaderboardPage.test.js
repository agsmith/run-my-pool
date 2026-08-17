import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import PoolLeaderboardPage from '../pages/pool/[id]/leaderboard';

process.env.NEXT_PUBLIC_API_URL = '';
const mockReplace = jest.fn();
jest.mock('next/router', () => ({
  useRouter: () => ({ isReady: true, query: { id: 'pool-1' }, replace: mockReplace }),
}));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);

const response = (data, ok = true) => Promise.resolve({
  ok,
  json: () => Promise.resolve(data),
});

describe('PoolLeaderboardPage', () => {
  beforeEach(() => {
    mockReplace.mockReset();
    localStorage.setItem('access_token', 'token');
    global.fetch = jest.fn((url) => {
      const path = String(url);
      if (path === '/pools/pool-1') return response({ id: 'pool-1', name: 'Office Survivor', pool_type: 'survivor' });
      if (path === '/pools/pool-1/is-admin') return response({ has_admin_access: false });
      if (path === '/picks/pool/pool-1/leaderboard') return response([
        { rank: 1, entry_id: 'entry-1', entry_name: 'Alpha Blitz', user_email: 'alpha@example.com', correct_picks: 4, completed_picks: 4, alive: true, picks: [{ week: 1, team: 'BUF', result: 'win' }, { week: 2, team: 'MIA', result: 'win' }] },
        { rank: 2, entry_id: 'entry-2', entry_name: 'Goal Line', user_email: 'goal@example.com', correct_picks: 2, completed_picks: 3, alive: false, picks: [{ week: 1, team: 'DAL', result: 'loss' }] },
      ]);
      throw new Error(`Unexpected request ${path}`);
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('shows every ranked entry and its revealed pick history', async () => {
    render(<PoolLeaderboardPage />);

    expect(await screen.findByText('Alpha Blitz')).toBeInTheDocument();
    expect(screen.getByText('Goal Line')).toBeInTheDocument();
    expect(screen.getByLabelText('Rank 1')).toHaveTextContent('1');
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('Eliminated')).toBeInTheDocument();
    expect(screen.getByLabelText('Alpha Blitz revealed picks')).toHaveTextContent('W1 BUF');
    expect(screen.getByRole('link', { name: 'Leaderboard' })).toHaveAttribute('aria-current', 'page');
  });

  test('shows a scoped error when leaderboard access fails', async () => {
    global.fetch = jest.fn((url) => String(url).includes('/leaderboard')
      ? response({ detail: 'Pool membership required' }, false)
      : response({ id: 'pool-1', name: 'Office Survivor', pool_type: 'survivor' }));

    render(<PoolLeaderboardPage />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load the leaderboard.');
  });
});
