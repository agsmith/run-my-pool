import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import PickEmBreakdownPage from '../pages/pool/[id]/breakdown';

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

describe('PickEmBreakdownPage', () => {
  beforeEach(() => {
    mockReplace.mockReset();
    localStorage.setItem('access_token', 'token');
    global.fetch = jest.fn((url) => {
      const path = String(url);
      if (path === '/pools/pool-1') return response({ id: 'pool-1', name: "Foy's Pick Em", pool_type: 'pickem' });
      if (path === '/pools/pool-1/activity-summary') return response({ week: 2 });
      if (path === '/pools/pool-1/lock-status') return response({ weeks: { 2: { locked: true, deadline: '2026-09-20T17:00:00Z' } } });
      if (path === '/pools/pool-1/is-admin') return response({ has_admin_access: false });
      if (path === '/picks/pool/pool-1/week/2/breakdown') return response([
        { team: 'BUF', team_abbrv: 'BUF', result: 'win', count: 1, entries: [{ entry_id: 'entry-1', entry_name: 'Sunday Sharp' }] },
        { team: 'MIA', team_abbrv: 'MIA', result: 'loss', count: 1, entries: [{ entry_id: 'entry-1', entry_name: 'Sunday Sharp' }] },
      ]);
      if (path === '/picks/pool/pool-1/weekly-standings/2') return response([
        { rank: 1, entry_id: 'entry-1', entry_name: 'Sunday Sharp', user_display_name: 'Alex Smith', points: 1, completed_picks: 2, predicted_total: 47 },
      ]);
      throw new Error(`Unexpected request ${path}`);
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('shows app-style weekly standings, pick results, and tiebreaker', async () => {
    render(<PickEmBreakdownPage />);

    expect(await screen.findByText('Alex Smith')).toBeInTheDocument();
    expect(screen.getByText('Sunday Sharp')).toBeInTheDocument();
    expect(screen.getByLabelText('Rank 1')).toHaveTextContent('#1');
    expect(screen.getByText('1', { selector: '.pick-breakdown-entry__wins strong' })).toBeInTheDocument();
    expect(screen.getByLabelText('Sunday Sharp Week 2 picks')).toHaveTextContent('BUF · W');
    expect(screen.getByLabelText('Sunday Sharp Week 2 picks')).toHaveTextContent('MIA · L');
    expect(screen.getByLabelText('Sunday Sharp Week 2 picks')).toHaveTextContent('Total: 47');
    expect(screen.getByRole('link', { name: 'Pick Breakdown' })).toHaveAttribute('aria-current', 'page');
  });

  test('keeps picks hidden until the selected week locks', async () => {
    global.fetch = jest.fn((url) => {
      const path = String(url);
      if (path === '/pools/pool-1') return response({ id: 'pool-1', name: "Foy's Pick Em", pool_type: 'pickem' });
      if (path === '/pools/pool-1/activity-summary') return response({ week: 2 });
      if (path === '/pools/pool-1/lock-status') return response({ weeks: { 2: { locked: false, deadline: '2099-09-20T17:00:00Z' } } });
      if (path === '/pools/pool-1/is-admin') return response({ has_admin_access: false });
      throw new Error(`Unexpected request ${path}`);
    });

    render(<PickEmBreakdownPage />);

    expect(await screen.findByText('Week 2 picks will appear after the weekly lock.')).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalledWith(expect.stringContaining('/breakdown'), expect.anything());
  });
});
