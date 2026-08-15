import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SquaresPage from '../pages/pool/[id]/squares';

process.env.NEXT_PUBLIC_API_URL = '';
jest.mock('next/router', () => ({ useRouter: () => ({ query: { id: 'pool-1' } }) }));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);
jest.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { id: 'user-1' } }) }));

const board = {
  pool_id: 'pool-1', pool_name: 'Sunday Squares', locked: false, locked_at: null,
  home_digits: null, away_digits: null, pot_mode: 'fixed', total_pot_cents: null, per_square_cents: null, claims: [], payouts: [],
  plan: 'commissioner', block_limit: 100,
  permissions: { is_admin: true, can_claim: true, can_admin_assign: true, can_use_variable_pot: true },
  game: { game_id: 1, start_time: '2026-09-13T17:00:00Z', status: 'scheduled', home_team: { abbrv: 'MIA' }, away_team: { abbrv: 'BUF' } },
};
const response = (data, ok = true) => Promise.resolve({ ok, status: 200, json: () => Promise.resolve(data) });

describe('SquaresPage', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'token');
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    jest.spyOn(window, 'print').mockImplementation(() => {});
  });
  afterEach(() => { jest.restoreAllMocks(); localStorage.clear(); });

  test('renders 100 hidden cells and claims an available square', async () => {
    global.fetch = jest.fn((url, options = {}) => {
      if (options.method === 'POST' && String(url).endsWith('/claims')) return response({ id: 'claim-1' });
      return response(board);
    });
    const user = userEvent.setup();
    render(<SquaresPage />);
    expect(await screen.findByRole('heading', { name: 'BUF at MIA' })).toBeInTheDocument();
    expect(screen.getAllByRole('gridcell')).toHaveLength(100);
    expect(screen.getByRole('gridcell', { name: 'Block 1, available' })).toBeInTheDocument();
    expect(screen.getByRole('gridcell', { name: 'Block 100, available' })).toBeInTheDocument();
    expect(screen.getAllByText('?')).toHaveLength(20);
    await user.click(screen.getAllByRole('gridcell')[0]);
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/squares/pool-1/claims', expect.objectContaining({ method: 'POST' })));
    expect(JSON.parse(fetch.mock.calls.find(([, options]) => options?.method === 'POST')[1].body)).toEqual({ row_index: 0, column_index: 0 });
  });

  test('shows immutable randomized digits and quarter winner after lock', async () => {
    global.fetch = jest.fn(() => response({ ...board, locked: true, home_digits: [0,1,2,3,4,5,6,7,8,9], away_digits: [9,8,7,6,5,4,3,2,1,0], payouts: [{ checkpoint: 'q1', home_score: 7, away_score: 3, winner_email: 'winner@example.com', amount_cents: 2500 }] }));
    render(<SquaresPage />);
    expect(await screen.findByText('winner@example.com')).toBeInTheDocument();
    expect(screen.getByText('$25.00 recorded')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /lock & randomize/i })).not.toBeInTheDocument();
    expect(screen.getAllByRole('gridcell')[0]).toBeDisabled();
  });

  test('lets an admin configure the pot in dollars and sends integer cents', async () => {
    global.fetch = jest.fn((url, options = {}) => {
      if (options.method === 'PATCH') return response({ ...board, total_pot_cents: 12345 });
      return response({ ...board, total_pot_cents: 10000 });
    });
    const user = userEvent.setup();
    render(<SquaresPage />);

    const potInput = await screen.findByRole('spinbutton', { name: 'Total pot ($)' });
    expect(potInput).toHaveValue(100);
    await user.clear(potInput);
    await user.type(potInput, '123.45');
    await user.click(screen.getByRole('button', { name: 'Save payouts' }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/squares/pool-1/payouts', expect.objectContaining({ method: 'PATCH' })));
    const request = fetch.mock.calls.find(([, options]) => options?.method === 'PATCH')[1];
    expect(JSON.parse(request.body)).toEqual({ pot_mode: 'fixed', total_pot_cents: 12345, per_square_cents: null, q1_percent: 25, halftime_percent: 25, q3_percent: 25, final_percent: 25 });
    expect(await screen.findByText('$123.45')).toBeInTheDocument();
  });

  test('lets an admin calculate the pot from a dollar amount per reserved block', async () => {
    global.fetch = jest.fn((url, options = {}) => {
      if (options.method === 'PATCH') return response({ ...board, pot_mode: 'per_square', total_pot_cents: 750, per_square_cents: 250 });
      return response({ ...board, pot_mode: 'per_square', total_pot_cents: 500, per_square_cents: 250 });
    });
    const user = userEvent.setup();
    render(<SquaresPage />);

    expect(await screen.findByText('$5.00')).toBeInTheDocument();
    expect(screen.getByText('$2.50 per reserved block')).toBeInTheDocument();
    const rateInput = screen.getByRole('spinbutton', { name: 'Amount per reserved block ($)' });
    expect(rateInput).toHaveValue(2.5);
    await user.clear(rateInput);
    await user.type(rateInput, '3.75');
    await user.click(screen.getByRole('button', { name: 'Save payouts' }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/squares/pool-1/payouts', expect.objectContaining({ method: 'PATCH' })));
    const request = fetch.mock.calls.find(([, options]) => options?.method === 'PATCH')[1];
    expect(JSON.parse(request.body)).toEqual({ pot_mode: 'per_square', total_pot_cents: null, per_square_cents: 375, q1_percent: 25, halftime_percent: 25, q3_percent: 25, final_percent: 25 });
  });

  test('shows members the pot and reservation owners without admin controls', async () => {
    global.fetch = jest.fn(() => response({
      ...board,
      total_pot_cents: 50000,
      permissions: { is_admin: false, can_claim: true },
      claims: [{ id: 'claim-1', row_index: 0, column_index: 0, user_id: 'user-2', user_email: 'owner@example.com', display_name: null }],
    }));
    render(<SquaresPage />);

    expect(await screen.findByText('$500.00')).toBeInTheDocument();
    expect(screen.getByText('owner@example.com')).toBeInTheDocument();
    expect(screen.getByRole('gridcell', { name: 'Block 1, reserved by owner@example.com' })).toBeDisabled();
    expect(screen.queryByRole('heading', { name: 'Admin payout setup' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /lock & randomize/i })).not.toBeInTheDocument();
  });

  test('shows the free loss-leader limit and paid feature upgrade path', async () => {
    global.fetch = jest.fn(() => response({
      ...board,
      plan: 'free', block_limit: 25,
      permissions: { is_admin: true, can_claim: false, can_admin_assign: false, can_use_variable_pot: false },
    }));
    render(<SquaresPage />);

    expect(await screen.findByText('Free Squares board')).toBeInTheDocument();
    expect(screen.getByText(/0 of 25 included blocks/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Upgrade to Commish' })).toHaveAttribute('href', '/pricing?checkout=commissioner');
    expect(screen.queryByRole('button', { name: 'Assign block' })).not.toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /Per reserved block/i })).toBeDisabled();
    expect(screen.getByRole('gridcell', { name: 'Block 1, available' })).toBeDisabled();
  });

  test('explains a full free board to members without showing them billing actions', async () => {
    global.fetch = jest.fn(() => response({
      ...board,
      plan: 'free', block_limit: 25,
      permissions: { is_admin: false, can_claim: false, can_admin_assign: false, can_use_variable_pot: false },
    }));
    render(<SquaresPage />);

    expect(await screen.findByText('Reservation limit reached')).toBeInTheDocument();
    expect(screen.getByText(/ask the pool commissioner to upgrade/i)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Upgrade to Commish' })).not.toBeInTheDocument();
  });

  test('opens the browser print dialog for printing or PDF export', async () => {
    global.fetch = jest.fn(() => response(board));
    const user = userEvent.setup();
    render(<SquaresPage />);

    await user.click(await screen.findByRole('button', { name: 'Print / Save PDF' }));
    expect(window.print).toHaveBeenCalledTimes(1);
  });

  test('lets an admin assign block 36 directly to a selected member', async () => {
    global.fetch = jest.fn((url, options = {}) => {
      if (options.method === 'POST' && String(url).endsWith('/claims')) return response({ id: 'claim-36' });
      return response({ ...board, members: [{ id: 'user-2', email: 'player@example.com' }] });
    });
    const user = userEvent.setup();
    render(<SquaresPage />);

    await user.selectOptions(await screen.findByLabelText('Member'), 'user-2');
    await user.type(screen.getByLabelText('Block number'), '36');
    await user.click(screen.getByRole('button', { name: 'Assign block' }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/squares/pool-1/claims', expect.objectContaining({ method: 'POST' })));
    const request = fetch.mock.calls.find(([, options]) => options?.method === 'POST')[1];
    expect(JSON.parse(request.body)).toEqual({ row_index: 3, column_index: 5, user_id: 'user-2' });
  });
});
