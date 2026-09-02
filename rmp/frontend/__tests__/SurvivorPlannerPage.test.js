import '@testing-library/jest-dom';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SurvivorPlannerPage from '../pages/pool/[id]/planner';

process.env.NEXT_PUBLIC_API_URL = '';
jest.mock('next/router', () => ({ useRouter: () => ({ isReady: true, query: { id: 'pool-1' } }) }));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);

const base = {
  pool: { id: 'pool-1', name: 'Office Survivor', pool_type: 'survivor', survivor_objective: 'win' },
  current_week: 1,
  entries: [{ id: 'entry-1', name: 'My Path', alive: true, picks: [], plans: [] }],
  weeks: Array.from({ length: 18 }, (_, index) => ({ week: index + 1, games: index < 2 ? [{ game_id: index + 1, home_team: { id: 1, name: 'Buffalo Bills', abbrv: 'BUF', logo: '/nfl/buf.svg' }, away_team: { id: 2, name: 'Miami Dolphins', abbrv: 'MIA', logo: '/nfl/mia.svg' }, official_line: null }] : [] })),
};
const response = (body, ok = true) => Promise.resolve({ ok, json: () => Promise.resolve(body) });
const matchupsByWeek = {
  1: [{ game_id: 1, official_line: null, live_line: { favorite_team_id: 1, spread: 7, details: 'BUF -7', provider: 'ESPN' } }],
  2: [{ game_id: 2, official_line: null, live_line: { favorite_team_id: 2, spread: 3, details: 'MIA -3', provider: 'ESPN' } }],
};
const matchupResponse = (url) => response(matchupsByWeek[Number(String(url).match(/week\/(\d+)/)?.[1])] || []);

describe('Survivor season planner', () => {
  beforeEach(() => { localStorage.setItem('access_token', 'token'); });
  afterEach(() => { jest.restoreAllMocks(); localStorage.clear(); });

  test('explains plan privacy, saves a future plan, and keeps official submission explicit', async () => {
    let state = JSON.parse(JSON.stringify(base));
    global.fetch = jest.fn((url, options = {}) => {
      if (url.includes('/schedule/')) return matchupResponse(url);
      if (options.method === 'PUT') {
        state.entries[0].plans = [{ id: 'plan-1', week: 1, team: 'BUF', team_id: 1 }];
        return response(state.entries[0].plans[0]);
      }
      if (options.method === 'POST') {
        state.entries[0].picks = [{ id: 'pick-1', week: 1, team: 'BUF', team_id: 1, locked: false }];
        state.entries[0].plans = [];
        return response(state.entries[0].picks[0]);
      }
      return response(JSON.parse(JSON.stringify(state)));
    });
    const user = userEvent.setup();
    render(<SurvivorPlannerPage />);

    expect(await screen.findByRole('heading', { name: 'Survivor Season Planner' })).toBeInTheDocument();
    expect(screen.getByText(/visible only to you/i)).toBeInTheDocument();
    expect(await screen.findByRole('combobox', { name: 'Entry' })).toHaveValue('entry-1');
    expect(await screen.findByText('Point spread -7')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/schedule/week/1/matchups?pool_id=pool-1');
    expect(fetch).toHaveBeenCalledWith('/schedule/week/2/matchups?pool_id=pool-1');
    expect(await screen.findByText('Point spreads loaded for all 2 scheduled weeks')).toBeInTheDocument();
    expect(screen.getAllByAltText('')).toHaveLength(4);
    await user.click(screen.getAllByRole('button', { name: /Buffalo Bills, week 1/ })[0]);
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/survivor-planner/entries/entry-1/weeks/1', expect.objectContaining({ method: 'PUT' })));
    await waitFor(() => expect(screen.getAllByRole('button', { name: /Buffalo Bills, week 1, planned/ })[0]).toHaveClass('is-planned'));
    expect(await screen.findByRole('button', { name: 'Make official pick' })).toBeInTheDocument();
    expect(screen.getByText(/not your official pick yet/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Make official pick' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/survivor-planner/entries/entry-1/weeks/1/make-official', expect.objectContaining({ method: 'POST' })));
  });

  test('makes an eliminated entry read-only', async () => {
    global.fetch = jest.fn((url) => url.includes('/schedule/') ? matchupResponse(url) : response({ ...base, entries: [{ ...base.entries[0], alive: false }] }));
    render(<SurvivorPlannerPage />);
    expect(await screen.findByText(/entry has been eliminated/i)).toBeInTheDocument();
    screen.getAllByRole('button', { name: /Buffalo Bills, week 1/ }).forEach((button) => expect(button).toBeDisabled());
  });

  test('keeps used teams ranked by point spread while making them unselectable', async () => {
    const used = { ...base, entries: [{ ...base.entries[0], picks: [{ id: 'pick-2', week: 2, team: 'BUF', team_id: 1 }] }] };
    global.fetch = jest.fn((url) => url.includes('/schedule/') ? matchupResponse(url) : response(used));
    render(<SurvivorPlannerPage />);

    expect(await screen.findByText('Point spread -7')).toBeInTheDocument();
    const buffalo = within(screen.getByRole('table')).getByRole('button', { name: /Buffalo Bills, week 1.*picked in week 2.*unavailable.*point spread -7/ });
    expect(buffalo).toBeDisabled();
    expect(buffalo).toHaveClass('has-spread', 'is-used');
    expect(within(buffalo).getByText('Picked W2')).toBeInTheDocument();
    const weeklyChoices = within(screen.getByRole('region', { name: 'Week 1 choices' })).getAllByRole('button');
    expect(weeklyChoices[0]).toHaveAccessibleName(/Buffalo Bills/);
    expect(within(weeklyChoices[0]).getByText('Picked Week 2 — unavailable')).toBeInTheDocument();
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/schedule/week/1/matchups'))).toHaveLength(1);
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/schedule/week/2/matchups'))).toHaveLength(1);
    expect(screen.getByText(/Plans are private and never count as picks/)).toHaveClass('planner-note--prominent');
  });

  test('uses distinct favorite, underdog, and planned-pick colors', async () => {
    const planned = { ...base, entries: [{ ...base.entries[0], plans: [{ id: 'plan-1', week: 1, team: 'BUF', team_id: 1 }] }] };
    global.fetch = jest.fn((url) => url.includes('/schedule/') ? matchupResponse(url) : response(planned));
    render(<SurvivorPlannerPage />);

    const buffalo = (await screen.findAllByRole('button', { name: /Buffalo Bills, week 1, planned.*point spread -7/ }))[0];
    const miami = screen.getAllByRole('button', { name: /Miami Dolphins, week 1.*point spread \+7/ })[0];
    expect(buffalo.style.getPropertyValue('--planner-heat')).toContain('22, 163, 74');
    expect(miami.style.getPropertyValue('--planner-heat')).toContain('220, 38, 38');
    expect(buffalo).toHaveClass('is-planned');
    expect(screen.getByText(/violet marks planned picks/i)).toBeInTheDocument();
  });

  test('preloads and ranks another scheduled week from favorite to underdog', async () => {
    global.fetch = jest.fn((url) => url.includes('/schedule/') ? matchupResponse(url) : response(base));
    const user = userEvent.setup();
    render(<SurvivorPlannerPage />);

    await user.click(await screen.findByRole('button', { name: 'W2' }));

    const choices = within(screen.getByRole('region', { name: 'Week 2 choices' })).getAllByRole('button');
    expect(choices[0]).toHaveAccessibleName(/Miami Dolphins/);
    expect(choices[0]).toHaveTextContent('Point spread -3');
    expect(choices[0].style.getPropertyValue('--planner-heat')).toContain('22, 163, 74');
    expect(choices[1]).toHaveAccessibleName(/Buffalo Bills/);
    expect(choices[1]).toHaveTextContent('Point spread +3');
    expect(choices[1].style.getPropertyValue('--planner-heat')).toContain('220, 38, 38');
  });

  test('clears unlocked plans for only the selected entry after confirmation', async () => {
    let state = { ...base, entries: [{ ...base.entries[0], plans: [
      { id: 'plan-1', week: 1, team: 'BUF', team_id: 1 },
      { id: 'plan-2', week: 2, team: 'MIA', team_id: 2 },
    ] }] };
    global.fetch = jest.fn((url, options = {}) => {
      if (url.includes('/schedule/')) return matchupResponse(url);
      if (options.method === 'DELETE' && url.endsWith('/plans')) {
        state = { ...state, entries: [{ ...state.entries[0], plans: [] }] };
        return response({ message: 'Unlocked plans cleared', cleared: 2, retained: 0 });
      }
      return response(JSON.parse(JSON.stringify(state)));
    });
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();
    render(<SurvivorPlannerPage />);

    await user.click(await screen.findByRole('button', { name: 'Reset' }));

    expect(window.confirm).toHaveBeenCalledWith(expect.stringMatching(/My Path.*Official picks and locked selections will remain/));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      '/survivor-planner/entries/entry-1/plans',
      expect.objectContaining({ method: 'DELETE' }),
    ));
    expect(await screen.findByRole('status')).toHaveTextContent('2 unlocked planned selections cleared');
    expect(screen.getByRole('button', { name: 'Reset' })).toBeDisabled();
  });
});
