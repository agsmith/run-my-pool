import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SurvivorPlannerPage from '../pages/pool/[id]/planner';

process.env.NEXT_PUBLIC_API_URL = '';
jest.mock('next/router', () => ({ useRouter: () => ({ isReady: true, query: { id: 'pool-1' } }) }));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);

const base = {
  pool: { id: 'pool-1', name: 'Office Survivor', pool_type: 'survivor', survivor_objective: 'win' },
  current_week: 1,
  entries: [{ id: 'entry-1', name: 'My Path', alive: true, picks: [], plans: [] }],
  weeks: Array.from({ length: 18 }, (_, index) => ({ week: index + 1, games: index < 2 ? [{ game_id: index + 1, home_team: { id: 1, name: 'Buffalo Bills', abbrv: 'BUF' }, away_team: { id: 2, name: 'Miami Dolphins', abbrv: 'MIA' }, official_line: null }] : [] })),
};
const response = (body, ok = true) => Promise.resolve({ ok, json: () => Promise.resolve(body) });

describe('Survivor season planner', () => {
  beforeEach(() => { localStorage.setItem('access_token', 'token'); });
  afterEach(() => { jest.restoreAllMocks(); localStorage.clear(); });

  test('explains plan privacy, saves a future plan, and keeps official submission explicit', async () => {
    let state = JSON.parse(JSON.stringify(base));
    global.fetch = jest.fn((url, options = {}) => {
      if (options.method === 'PUT') {
        state.entries[0].plans = [{ id: 'plan-1', week: 1, team: 'BUF', team_id: 1 }];
        return response(state.entries[0].plans[0]);
      }
      if (options.method === 'POST') {
        state.entries[0].picks = [{ id: 'pick-1', week: 1, team: 'BUF', team_id: 1, locked: false }];
        state.entries[0].plans = [];
        return response(state.entries[0].picks[0]);
      }
      return response(state);
    });
    const user = userEvent.setup();
    render(<SurvivorPlannerPage />);

    expect(await screen.findByRole('heading', { name: 'Survivor Season Planner' })).toBeInTheDocument();
    expect(screen.getByText(/visible only to you/i)).toBeInTheDocument();
    expect(await screen.findByRole('combobox', { name: 'Entry' })).toHaveValue('entry-1');
    await user.click(screen.getAllByRole('button', { name: 'Buffalo Bills, week 1' })[0]);
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/survivor-planner/entries/entry-1/weeks/1', expect.objectContaining({ method: 'PUT' })));
    expect(await screen.findByRole('button', { name: 'Make official pick' })).toBeInTheDocument();
    expect(screen.getByText(/not your official pick yet/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Make official pick' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/survivor-planner/entries/entry-1/weeks/1/make-official', expect.objectContaining({ method: 'POST' })));
  });

  test('makes an eliminated entry read-only', async () => {
    global.fetch = jest.fn(() => response({ ...base, entries: [{ ...base.entries[0], alive: false }] }));
    render(<SurvivorPlannerPage />);
    expect(await screen.findByText(/entry has been eliminated/i)).toBeInTheDocument();
    screen.getAllByRole('button', { name: 'Buffalo Bills, week 1' }).forEach((button) => expect(button).toBeDisabled());
  });
});
