import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PickEmPage from '../pages/pool/[id]/pickem';

process.env.NEXT_PUBLIC_API_URL = '';
const mockReplace = jest.fn();
jest.mock('next/router', () => ({
  useRouter: () => ({ query: { id: 'pool-1' }, replace: mockReplace }),
}));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);

const response = (data, ok = true) => Promise.resolve({
  ok,
  json: () => Promise.resolve(data),
});

describe('PickEmPage', () => {
  beforeEach(() => {
    mockReplace.mockReset();
    localStorage.setItem('access_token', 'token');
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('shows every game without spreads and saves one winner for the selected entry', async () => {
    const game = {
      game_id: 101,
      start_time: '2026-09-13T17:00:00Z',
      away_team: { id: 1, abbrv: 'BUF', name: 'Buffalo Bills' },
      home_team: { id: 2, abbrv: 'MIA', name: 'Miami Dolphins' },
    };
    global.fetch = jest.fn((url, options = {}) => {
      const path = String(url);
      if (path === '/pools/pool-1') return response({ id: 'pool-1', name: 'Office Pick Em', pool_type: 'pickem' });
      if (path === '/entries/pool/pool-1') return response([{ id: 'entry-1', name: 'My Card' }]);
      if (path === '/picks/pool/pool-1/standings') return response([{ rank: 1, entry_id: 'entry-1', entry_name: 'My Card', user_display_name: 'me', points: 4, possible_points: 5 }]);
      if (path === '/picks/pool/pool-1/weekly-standings/1') return response([]);
      if (path === '/schedule/week/1') return response([game]);
      if (path === '/picks/entry/entry-1') return response([]);
      if (path === '/picks/create' && options.method === 'POST') {
        expect(JSON.parse(options.body)).toEqual({ entry_id: 'entry-1', week: 1, game_id: 101, team: 'BUF' });
        return response({ id: 'pick-1', entry_id: 'entry-1', week: 1, game_id: 101, team: 'BUF' });
      }
      throw new Error(`Unexpected request ${path}`);
    });

    const user = userEvent.setup();
    render(<PickEmPage />);

    expect(await screen.findByRole('button', { name: /BUF Buffalo Bills/ })).toBeInTheDocument();
    expect(screen.getByTitle('BUF')).toHaveAttribute('src', '/nfl/buf.svg');
    expect(screen.getByText('Office Pick Em')).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '4' })).toBeInTheDocument();
    expect(screen.queryByText(/official line|live line|line pending/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /BUF Buffalo Bills/ }));

    await waitFor(() => expect(screen.getByText('1 / 1 selected')).toBeInTheDocument());
    expect(global.fetch).toHaveBeenCalledWith('/picks/create', expect.objectContaining({ method: 'POST' }));
  });

  test('redirects survivor pools to the survivor entries page', async () => {
    global.fetch = jest.fn((url) => {
      const path = String(url);
      if (path === '/pools/pool-1') return response({ id: 'pool-1', pool_type: 'survivor' });
      if (path === '/entries/pool/pool-1' || path === '/picks/pool/pool-1/standings' || path === '/picks/pool/pool-1/weekly-standings/1' || path === '/schedule/week/1') return response([]);
      throw new Error(`Unexpected request ${path}`);
    });

    render(<PickEmPage />);
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/pool/pool-1/entries'));
  });

  test('prominently directs a member without entries to create their first entry', async () => {
    global.fetch = jest.fn((url) => {
      const path = String(url);
      if (path === '/pools/pool-1') return response({ id: 'pool-1', name: 'Office Pick Em', pool_type: 'pickem' });
      if (path === '/entries/pool/pool-1' || path === '/picks/pool/pool-1/standings' || path === '/picks/pool/pool-1/weekly-standings/1' || path === '/schedule/week/1') return response([]);
      throw new Error(`Unexpected request ${path}`);
    });

    render(<PickEmPage />);

    expect(await screen.findByRole('heading', { name: /create an entry to start picking/i })).toBeInTheDocument();
    expect(screen.getByText(/your entry is your pick 'em card for the season/i)).toBeInTheDocument();
    expect(screen.getByText('No entries yet')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /create your first entry/i })).toHaveAttribute(
      'href',
      '/pool/pool-1/entries/create',
    );
    expect(screen.queryByRole('combobox', { name: /entry/i })).not.toBeInTheDocument();
  });

  test('limits a configured weekly slate while allowing an existing selection to change', async () => {
    const games = [101, 102].map((gameId, index) => ({
      game_id: gameId,
      start_time: '2026-09-13T17:00:00Z',
      away_team: { id: 10 + index * 2, abbrv: index ? 'GB' : 'BUF', name: index ? 'Green Bay Packers' : 'Buffalo Bills' },
      home_team: { id: 11 + index * 2, abbrv: index ? 'CHI' : 'MIA', name: index ? 'Chicago Bears' : 'Miami Dolphins' },
    }));
    global.fetch = jest.fn((url, options = {}) => {
      const path = String(url);
      if (path === '/pools/pool-1') return response({ id: 'pool-1', name: 'Five Game Pool', pool_type: 'pickem', pickem_games_per_week: 1 });
      if (path === '/entries/pool/pool-1') return response([{ id: 'entry-1', name: 'My Card' }]);
      if (path === '/picks/pool/pool-1/standings') return response([]);
      if (path === '/picks/pool/pool-1/weekly-standings/1') return response([]);
      if (path === '/schedule/week/1') return response(games);
      if (path === '/picks/entry/entry-1') return response([{ id: 'pick-1', entry_id: 'entry-1', week: 1, game_id: 101, team: 'BUF' }]);
      if (path === '/picks/create' && options.method === 'POST') return response({ id: 'pick-1', entry_id: 'entry-1', week: 1, game_id: 101, team: 'MIA' });
      throw new Error(`Unexpected request ${path}`);
    });

    const user = userEvent.setup();
    render(<PickEmPage />);

    expect(await screen.findByText('1 / 1 selected')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /GB Green Bay Packers/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /MIA Miami Dolphins/i })).toBeEnabled();
    await user.click(screen.getByRole('button', { name: /MIA Miami Dolphins/i }));
    expect(global.fetch).toHaveBeenCalledWith('/picks/create', expect.objectContaining({ method: 'POST' }));
  });
});
