import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PickEmPrintablePage from '../pages/admin/league/[id]/pickem-printable';

process.env.NEXT_PUBLIC_API_URL = '';
const mockPush = jest.fn();
jest.mock('next/router', () => ({
  useRouter: () => ({ query: { id: 'pool-1', week: '3' }, push: mockPush }),
}));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);

const sheet = {
  pool_id: 'pool-1', pool_name: 'Sunday Bar Pool', week: 3,
  slate: 'sunday_monday', required_picks: 2, requires_tiebreaker: true,
  games: [
    {
      game_id: 101, start_time: '2026-09-20T17:00:00Z',
      away_team: { abbrv: 'BUF', name: 'Buffalo Bills' },
      home_team: { abbrv: 'MIA', name: 'Miami Dolphins' },
    },
    {
      game_id: 102, start_time: '2026-09-22T00:15:00Z',
      away_team: { abbrv: 'GB', name: 'Green Bay Packers' },
      home_team: { abbrv: 'CHI', name: 'Chicago Bears' },
    },
  ],
};

describe('PickEmPrintablePage', () => {
  beforeEach(() => {
    mockPush.mockReset();
    localStorage.setItem('access_token', 'token');
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(sheet) }));
    window.print = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('renders the authorized weekly slate and prints it', async () => {
    const user = userEvent.setup();
    render(<PickEmPrintablePage />);

    expect(await screen.findByRole('heading', { name: 'Sunday Bar Pool' })).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith('/admin/pools/pool-1/pickem-printable/3', expect.objectContaining({ headers: { Authorization: 'Bearer token' } }));
    expect(screen.getByText(/one winner for every matchup/i)).toBeInTheDocument();
    expect(screen.getByText('NAME')).toBeInTheDocument();
    expect(screen.getByText('BUF')).toBeInTheDocument();
    expect(screen.getByText('MIA')).toBeInTheDocument();
    expect(screen.getByText(/Buffalo Bills vs Miami Dolphins/)).toBeInTheDocument();
    expect(screen.getByText(/Green Bay Packers vs Chicago Bears/)).toBeInTheDocument();
    expect(screen.getByText(/Late Monday Night Game — Total Score/i)).toBeInTheDocument();
    expect(screen.getByText('RunMyPool.net')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Print / Save PDF' }));
    expect(window.print).toHaveBeenCalledTimes(1);
  });

  test('changes weeks through the commissioner printable route', async () => {
    const user = userEvent.setup();
    render(<PickEmPrintablePage />);
    await screen.findByRole('heading', { name: 'Sunday Bar Pool' });
    await user.selectOptions(screen.getByLabelText('Printable week'), '4');
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/admin/league/pool-1/pickem-printable?week=4'));
  });
});
