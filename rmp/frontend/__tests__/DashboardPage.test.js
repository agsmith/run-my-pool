import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Dashboard from '../pages/dashboard';

process.env.NEXT_PUBLIC_API_URL = '';
const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockUser = { id: 'user-1', email: 'player@example.com' };
jest.mock('next/router', () => ({ useRouter: () => ({ push: mockPush, replace: mockReplace }) }));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);
jest.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: mockUser }) }));

const response = (data, ok = true) => Promise.resolve({
  ok,
  status: ok ? 200 : 500,
  json: () => Promise.resolve(data),
});

const pool = {
  id: 'pool-1', name: 'Office Survivor', description: 'Weekly pool',
  is_private: true, created_by: 'someone-else',
};

function installDashboardApi({ pools = [pool], admin = true, failPools = false } = {}) {
  global.fetch = jest.fn((url) => {
    const path = String(url);
    if (path.endsWith('/pools/my-pools')) return response(failPools ? { detail: 'failed' } : pools, !failPools);
    if (path.endsWith('/pools/pool-1/picks-summary')) {
      return response({ 1: { teams: { BUF: 1 }, unlockedCount: 0 } });
    }
    if (path.includes('/pools/pool-1/activity-summary?week=')) {
      return response({ entries_remaining: 12, week: 1, week_selections: 9 });
    }
    if (path.endsWith('/entries/pool/pool-1')) {
      return response([
        { id: 'entry-1', name: 'Alive', status: 'active' },
        { id: 'entry-2', name: 'Out', status: 'eliminated' },
      ]);
    }
    if (path.endsWith('/pools/pool-1/is-admin')) {
      return response({ has_admin_access: admin, is_owner: admin, is_admin: false });
    }
    throw new Error(`Unexpected request: ${path}`);
  });
}

describe('dashboard', () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockReplace.mockReset();
    localStorage.setItem('access_token', 'token');
    localStorage.removeItem('poolOrder');
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('summarizes entries and routes an authorized commissioner', async () => {
    installDashboardApi();
    const user = userEvent.setup();
    render(<Dashboard />);

    expect(await screen.findByRole('heading', { name: 'Office Survivor' })).toBeInTheDocument();
    expect(screen.getByText('Private')).toBeInTheDocument();
    expect(screen.getByText('Entries Remaining')).toBeInTheDocument();
    expect(screen.getByText('Week 1 Selections')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('9')).toBeInTheDocument();
    expect(screen.getByText('BUF')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /make or edit picks/i }));
    expect(mockPush).toHaveBeenCalledWith('/pool/pool-1/entries');
    expect(screen.queryByRole('button', { name: 'Forum' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Admin' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Office Survivor' }));
    expect(mockPush).toHaveBeenCalledWith('/pool/pool-1');
  });

  test('uses the same single pool-home entry point for a regular player', async () => {
    installDashboardApi({ admin: false });
    render(<Dashboard />);

    expect(await screen.findByRole('heading', { name: 'Office Survivor' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Office Survivor' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /make or edit picks/i })).toBeInTheDocument();
  });

  test('sends users with no pool memberships directly to Browse Pools', async () => {
    installDashboardApi({ pools: [] });
    render(<Dashboard />);

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/leagues'));
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test('surfaces pool-loading failures instead of rendering stale data', async () => {
    installDashboardApi({ failPools: true });
    render(<Dashboard />);

    expect(await screen.findByText('Failed to load leagues')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Office Survivor' })).not.toBeInTheDocument();
  });
});
