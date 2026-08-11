import '@testing-library/jest-dom';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LeagueEntries from '../pages/pool/[id]/entries';

const push = jest.fn();
const mockAuthenticatedUser = { id: 'user-1', email: 'player@example.com' };
jest.mock('next/router', () => ({
  useRouter: () => ({ isReady: true, query: { id: 'pool-1' }, push }),
}));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: mockAuthenticatedUser }),
}));

const jsonResponse = (data, ok = true) => Promise.resolve({
  ok,
  status: ok ? 200 : 400,
  json: () => Promise.resolve(data),
});

function installApi({ pool = {}, entries = [], picks = {}, lockWeeks = {} } = {}) {
  global.fetch = jest.fn((url, options = {}) => {
    const path = String(url);
    if (path.endsWith('/pools/pool-1')) {
      return jsonResponse({
        id: 'pool-1', name: 'Office Survivor', owner_id: 'owner-1',
        join_lock_time: null, ...pool,
      });
    }
    if (path.endsWith('/pools/pool-1/lock-status')) {
      return jsonResponse({ weeks: lockWeeks });
    }
    if (path.endsWith('/entries/pool/pool-1')) return jsonResponse(entries);
    const pickMatch = path.match(/\/picks\/entry\/([^/]+)$/);
    if (pickMatch) return jsonResponse(picks[pickMatch[1]] || []);
    if (path.includes('/picks/pool/pool-1/week/')) return jsonResponse([]);
    if (path.endsWith('/schedule/week/2')) {
      return jsonResponse([{
        game_id: 20,
        start_time: '2026-09-13T17:00:00Z',
        away_team: { id: 1, name: 'Buffalo Bills', abbrv: 'BUF', logo: '/nfl/buf.svg' },
        home_team: { id: 2, name: 'Miami Dolphins', abbrv: 'MIA', logo: '/nfl/mia.svg' },
      }]);
    }
    if (path.endsWith('/picks/create') && options.method === 'POST') {
      const request = JSON.parse(options.body);
      return jsonResponse({ id: 'pick-new', ...request, locked: false });
    }
    throw new Error(`Unexpected request: ${path}`);
  });
}

describe('player entries page', () => {
  beforeEach(() => {
    push.mockReset();
    localStorage.setItem('access_token', 'test-token');
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('preserves green winners and red loser while disabling remaining weeks', async () => {
    installApi({
      entries: [{ id: 'entry-1', name: 'One and Done', alive: false }],
      picks: {
        'entry-1': [
          { id: 'pick-1', week: 1, team: 'BUF', result: 'win', locked: true },
          { id: 'pick-2', week: 2, team: 'KC', result: 'loss', locked: true },
        ],
      },
    });

    render(<LeagueEntries />);

    const winner = await screen.findByTitle('BUF - win');
    const loser = screen.getByTitle('KC - loss');
    const row = screen.getByText('One and Done').closest('tr');
    const future = within(row).getByRole('button', { name: '3' });

    expect(winner).toHaveStyle({ backgroundColor: '#e8f5e9', borderColor: '#4caf50' });
    expect(loser).toHaveStyle({ backgroundColor: '#ffebee', borderColor: '#f44336' });
    expect(winner).toBeDisabled();
    expect(loser).toBeDisabled();
    expect(future).toBeDisabled();
    expect(future).toHaveAttribute('title', 'Entry eliminated - no remaining picks available');
  });

  test('hides entry management after registration lock and disables only locked weeks', async () => {
    installApi({
      pool: { join_lock_time: '2020-01-01T00:00:00' },
      entries: [{ id: 'entry-1', name: 'Still Alive', alive: true }],
      lockWeeks: {
        '1': { locked: true, deadline: '2026-09-06T17:00:00Z' },
        '2': { locked: false, deadline: '2026-09-13T17:00:00Z' },
      },
    });

    render(<LeagueEntries />);

    const locked = await screen.findByTitle('Week 1 is locked');
    const row = screen.getByText('Still Alive').closest('tr');
    const future = within(row).getByRole('button', { name: '2' });

    expect(locked).toBeDisabled();
    expect(future).toBeEnabled();
    expect(screen.queryByRole('button', { name: /create new entry/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete entry/i })).not.toBeInTheDocument();
    expect(screen.getByText(/locked weeks are read-only/i)).toBeInTheDocument();
  });

  test('opens an available week and saves a valid selection', async () => {
    const user = userEvent.setup();
    installApi({
      entries: [{ id: 'entry-1', name: 'Still Alive', alive: true }],
      lockWeeks: { '2': { locked: false, deadline: '2026-09-13T17:00:00Z' } },
    });
    render(<LeagueEntries />);

    const row = (await screen.findByText('Still Alive')).closest('tr');
    await user.click(within(row).getByRole('button', { name: '2' }));
    expect(await screen.findByRole('heading', { name: /week 2 matchups/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Buffalo Bills' }));
    await user.click(screen.getByRole('button', { name: 'Save Pick' }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/picks/create'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ entry_id: 'entry-1', week: 2, team: 'BUF' }),
      }),
    ));
    expect(screen.queryByRole('heading', { name: /week 2 matchups/i })).not.toBeInTheDocument();
  });
});
