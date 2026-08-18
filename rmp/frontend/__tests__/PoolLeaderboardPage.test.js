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
        { rank: 2, entry_id: 'entry-1', entry_name: 'Alpha Blitz', user_display_name: 'alpha', correct_picks: 0, completed_picks: 0, alive: true, picks: [] },
        { rank: 1, entry_id: 'entry-2', entry_name: 'Goal Line', user_display_name: 'goal', correct_picks: 2, completed_picks: 3, alive: false, picks: [{ week: 1, team: 'DAL', result: 'win' }, { week: 2, team: 'BUF', result: 'win' }, { week: 3, team: 'MIA', result: 'loss' }] },
      ]);
      throw new Error(`Unexpected request ${path}`);
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('shows only weeks survived and orders survivor entries highest to lowest', async () => {
    render(<PoolLeaderboardPage />);

    expect(await screen.findByText('Alpha Blitz')).toBeInTheDocument();
    expect(screen.getByText('Goal Line')).toBeInTheDocument();
    expect(screen.getByLabelText('Rank 1')).toHaveTextContent('1');
    expect(screen.getByLabelText('2 weeks survived')).toHaveTextContent('2');
    expect(screen.getByLabelText('0 weeks survived')).toHaveTextContent('0');
    expect(screen.queryByText('Correct')).not.toBeInTheDocument();
    expect(screen.queryByText('Final picks')).not.toBeInTheDocument();
    expect(screen.queryByText('Eliminated')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Goal Line revealed picks')).toHaveTextContent('W1 DAL');
    const entries = screen.getByRole('region', { name: 'Pool leaderboard' }).querySelectorAll('.leaderboard-entry');
    expect(entries[0]).toHaveTextContent('Goal Line');
    expect(entries[1]).toHaveTextContent('Alpha Blitz');
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
