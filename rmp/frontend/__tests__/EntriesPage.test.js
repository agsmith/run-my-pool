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

function installApi({ pool = {}, entries = [], picks = {}, lockWeeks = {}, createdEntry = null, createEntries = [], breakdown = [], breakdownByWeek = null } = {}) {
  let currentEntries = [...entries];
  let createIndex = 0;
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
    if (path.endsWith('/entries/pool/pool-1')) return jsonResponse(currentEntries);
    const pickMatch = path.match(/\/picks\/entry\/([^/]+)$/);
    if (pickMatch) return jsonResponse(picks[pickMatch[1]] || []);
    const breakdownMatch = path.match(/\/picks\/pool\/pool-1\/week\/(\d+)\/breakdown/);
    if (breakdownMatch) return jsonResponse(breakdownByWeek?.[breakdownMatch[1]] ?? breakdown);
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
    if (path.endsWith('/entries/create') && options.method === 'POST' && (createdEntry || createEntries.length)) {
      const requested = JSON.parse(options.body);
      const nextEntry = createEntries[createIndex++] || createdEntry || {
        id: `entry-${currentEntries.length + 1}`, name: requested.name, alive: true,
      };
      currentEntries = [...currentEntries, nextEntry];
      return jsonResponse(nextEntry);
    }
    const entryMatch = path.match(/\/entries\/([^/]+)$/);
    if (entryMatch && options.method === 'PUT') {
      const update = JSON.parse(options.body);
      currentEntries = currentEntries.map((entry) => (
        entry.id === entryMatch[1] ? { ...entry, ...update } : entry
      ));
      return jsonResponse(currentEntries.find((entry) => entry.id === entryMatch[1]));
    }
    if (entryMatch && options.method === 'DELETE') {
      currentEntries = currentEntries.filter((entry) => entry.id !== entryMatch[1]);
      return jsonResponse({ message: 'Entry deleted successfully' });
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

  test('keeps existing Week 1 picks visible after adding another entry', async () => {
    const user = userEvent.setup();
    installApi({
      entries: [{ id: 'entry-1', name: 'Entry 1', alive: true }],
      picks: { 'entry-1': [{ id: 'pick-1', week: 1, team: 'DET', locked: false }] },
      createdEntry: { id: 'entry-2', name: 'Entry 2', alive: true },
    });
    render(<LeagueEntries />);

    expect(await screen.findByAltText('DET logo')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /create new entry/i }));

    expect(await screen.findByText('Entry 2')).toBeInTheDocument();
    expect(screen.getByAltText('DET logo')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/picks/entry/entry-1'),
      expect.any(Object),
    );
  });

  test('requests server-generated names for consecutive entries', async () => {
    const user = userEvent.setup();
    installApi({
      entries: [{ id: 'entry-1', name: 'Entry 1', alive: true }],
      createEntries: [
        { id: 'entry-2', name: 'Entry 2', alive: true },
        { id: 'entry-3', name: 'Entry 3', alive: true },
      ],
    });
    render(<LeagueEntries />);

    await screen.findByText('Entry 1');
    await user.click(screen.getByRole('button', { name: /create new entry/i }));
    await screen.findByText('Entry 2');
    await user.click(screen.getByRole('button', { name: /create new entry/i }));
    await screen.findByText('Entry 3');

    const createBodies = fetch.mock.calls
      .filter(([url, options]) => String(url).endsWith('/entries/create') && options?.method === 'POST')
      .map(([, options]) => JSON.parse(options.body));
    expect(createBodies).toEqual([
      { pool_id: 'pool-1', generate_name: true },
      { pool_id: 'pool-1', generate_name: true },
    ]);
  });

  test('renders the Washington Commanders logo for WSH picks', async () => {
    installApi({
      entries: [{ id: 'entry-wsh', name: 'Commanders Pick', alive: true }],
      picks: { 'entry-wsh': [{ id: 'pick-wsh', week: 1, team: 'WSH', locked: false }] },
    });

    render(<LeagueEntries />);

    const logo = await screen.findByAltText('WSH logo');
    expect(logo).toHaveAttribute('src', '/nfl/wsh.svg');
    expect(logo).toHaveAttribute('title', 'WSH');
    expect(logo).toHaveClass('entries-team-logo', 'entries-team-logo--pick');
  });

  test('canceling a rename does not save the edited name', async () => {
    const user = userEvent.setup();
    installApi({ entries: [{ id: 'entry-1', name: 'Original Name', alive: true }] });
    render(<LeagueEntries />);

    await user.click(await screen.findByRole('button', { name: /original name/i }));
    const input = screen.getByDisplayValue('Original Name');
    await user.clear(input);
    await user.type(input, 'Changed Name');
    await user.click(screen.getByRole('button', { name: 'Cancel renaming Original Name' }));

    expect(screen.getByText('Original Name')).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining('/entries/entry-1'),
      expect.objectContaining({ method: 'PUT' }),
    );
  });

  test('deletes the explicitly selected entry regardless of creation or display order', async () => {
    const user = userEvent.setup();
    installApi({
      entries: [
        { id: 'old-entry', name: 'Zulu', alive: true, created_at: '2026-01-01T00:00:00Z' },
        { id: 'new-entry', name: 'Alpha', alive: true, created_at: '2026-02-01T00:00:00Z' },
      ],
    });
    render(<LeagueEntries />);

    await user.click(await screen.findByRole('button', { name: /delete entry/i }));
    await user.selectOptions(screen.getByLabelText('Entry'), 'old-entry');
    await user.click(screen.getByRole('button', { name: 'Delete Selected Entry' }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/entries/old-entry'),
      expect.objectContaining({ method: 'DELETE' }),
    ));
    expect(screen.queryByText('Zulu')).not.toBeInTheDocument();
    expect(screen.getByText('Alpha')).toBeInTheDocument();
  });

  test('hides entry deletion as soon as Week 1 locks', async () => {
    installApi({
      entries: [{ id: 'entry-1', name: 'Locked Entry', alive: true }],
      lockWeeks: { '1': { locked: true, deadline: '2026-09-06T17:00:00Z' } },
    });
    render(<LeagueEntries />);

    expect(await screen.findByText('Locked Entry')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete entry/i })).not.toBeInTheDocument();
  });

  test('opens a team count overlay with users and surviving entry counts', async () => {
    const user = userEvent.setup();
    installApi({
      entries: [{ id: 'entry-1', name: 'Alive', alive: true }],
      breakdown: [{
        team: 'BUF', team_id: 1, team_name: 'Buffalo Bills', team_abbrv: 'BUF', count: 3,
        users: [
          { user_id: 'user-1', display_name: 'player', entry_count: 2 },
          { user_id: 'user-2', display_name: 'friend', entry_count: 1 },
        ],
      }],
    });
    render(<LeagueEntries />);

    const breakdownLogo = await screen.findByAltText('BUF');
    expect(breakdownLogo).toHaveClass('entries-team-logo', 'entries-team-logo--breakdown');
    await user.click(await screen.findByRole('button', { name: 'Show users who picked BUF' }));
    const dialog = screen.getByRole('dialog', { name: 'BUF picks' });
    expect(within(dialog).getByText('player')).toBeInTheDocument();
    expect(within(dialog).getByText('friend')).toBeInTheDocument();
    expect(within(dialog).queryByText(/@example\.com/)).not.toBeInTheDocument();
    expect(within(dialog).getByText('2')).toBeInTheDocument();
    expect(within(dialog).getByText('1')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Close pick details' }));
    expect(screen.queryByRole('dialog', { name: 'BUF picks' })).not.toBeInTheDocument();
  });

  test('keeps pre-lock weeks hidden and loads a selected locked week', async () => {
    const user = userEvent.setup();
    installApi({
      entries: [{ id: 'entry-1', name: 'Alive', alive: true }],
      lockWeeks: { '1': { locked: false }, '2': { locked: true } },
      breakdownByWeek: {
        '1': [],
        '2': [{
          team: 'MIA', team_id: 2, team_name: 'Miami Dolphins', team_abbrv: 'MIA', count: 1,
          users: [{ user_id: 'user-1', display_name: 'player', entry_count: 1 }],
        }],
      },
    });
    render(<LeagueEntries />);

    expect(await screen.findByText('Alive')).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/picks/pool/pool-1/week/1/breakdown'),
      expect.any(Object),
    ));
    expect(screen.getByText('Week 1 picks will be revealed after the weekly lock time.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /show users who picked/i })).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Pick breakdown week'), '2');
    expect(await screen.findByRole('button', { name: 'Show users who picked MIA' })).toHaveTextContent('1');
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/picks/pool/pool-1/week/2/breakdown'),
      expect.any(Object),
    );
    expect(screen.getByText('🔒 Locked')).toBeInTheDocument();
  });

  test('explains when a selected locked week has no surviving picks', async () => {
    const user = userEvent.setup();
    installApi({
      entries: [{ id: 'entry-1', name: 'Alive', alive: true }],
      lockWeeks: { '3': { locked: true } },
      breakdownByWeek: { '1': [], '3': [] },
    });
    render(<LeagueEntries />);

    await user.selectOptions(await screen.findByLabelText('Pick breakdown week'), '3');

    expect(await screen.findByText('No surviving picks were recorded for Week 3.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Week 3 Pick Breakdown' })).toBeInTheDocument();
  });
});
