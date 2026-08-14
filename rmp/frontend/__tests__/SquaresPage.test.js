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
  home_digits: null, away_digits: null, claims: [], payouts: [],
  permissions: { is_admin: true, can_claim: true },
  game: { game_id: 1, start_time: '2026-09-13T17:00:00Z', status: 'scheduled', home_team: { abbrv: 'MIA' }, away_team: { abbrv: 'BUF' } },
};
const response = (data, ok = true) => Promise.resolve({ ok, status: 200, json: () => Promise.resolve(data) });

describe('SquaresPage', () => {
  beforeEach(() => { localStorage.setItem('access_token', 'token'); jest.spyOn(window, 'confirm').mockReturnValue(true); });
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
});
