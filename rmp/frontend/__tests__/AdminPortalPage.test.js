import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AdminPortal from '../pages/admin/league/[id]';

process.env.NEXT_PUBLIC_API_URL = '';

const mockPush = jest.fn();
const mockUser = { id: 'owner-1', email: 'owner@example.com' };
jest.mock('next/router', () => ({
  useRouter: () => ({ isReady: true, query: { id: 'pool-1' }, push: mockPush }),
}));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);
jest.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: mockUser }) }));
jest.mock('../components/AdminUserOverview', () => function MockOverview({ overview }) {
  return <div data-testid="user-overview">{overview ? `${overview.total_users} pool users` : 'No overview'}</div>;
});
jest.mock('../components/AdminAccessControl', () => function MockAccess() {
  return <div>Admin access control</div>;
});
jest.mock('../components/OwnershipTransferControl', () => function MockTransfer() {
  return <div>Ownership transfer control</div>;
});
jest.mock('../components/LeagueLockSettings', () => function MockLocks() {
  return <div>Pool lock settings</div>;
});
jest.mock('../components/LeaguePasswordViewer', () => function MockPassword() {
  return <div>Current password viewer</div>;
});

const league = {
  id: 'pool-1', name: 'Office Survivor', owner_id: 'owner-1', is_private: false,
  created_at: '2026-08-01T12:00:00Z',
};

const response = (data, ok = true) => Promise.resolve({
  ok,
  status: ok ? 200 : 400,
  json: () => Promise.resolve(data),
  blob: () => Promise.resolve(new Blob(['email,entry\n'])),
});

function installApi(overrides = {}) {
  global.fetch = jest.fn((url, options = {}) => {
    const path = String(url);
    const key = `${options.method || 'GET'} ${path}`;
    if (overrides[key]) return overrides[key](url, options);
    if (path.endsWith('/pools/pool-1') && !options.method) return response(league);
    if (path.endsWith('/pools')) return response([league]);
    if (path.endsWith('/admin/pools/pool-1/users-overview')) {
      return response({ total_users: 2, users: [] });
    }
    if (path.includes('/audit/')) return response([]);
    throw new Error(`Unexpected request: ${key}`);
  });
}

describe('commissioner portal', () => {
  beforeEach(() => {
    mockPush.mockReset();
    localStorage.setItem('access_token', 'token');
    installApi();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('loads only the selected league and exposes every management workspace', async () => {
    const user = userEvent.setup();
    render(<AdminPortal />);

    expect(await screen.findByRole('heading', { name: 'Office Survivor' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Pool Management' })).toBeInTheDocument();
    expect(screen.getByText('Pool lock settings')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /user management/i }));
    expect(screen.getByRole('heading', { name: 'User Management' })).toBeInTheDocument();
    expect(await screen.findByText('2 pool users')).toBeInTheDocument();
    expect(screen.getByText('Admin access control')).toBeInTheDocument();
    expect(screen.getByText('Ownership transfer control')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /entry management/i }));
    expect(screen.getByRole('heading', { name: 'Entry Management' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Correct Pick' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /audit log/i }));
    expect(screen.getByRole('heading', { name: 'Audit Log' })).toBeInTheDocument();
    expect(await screen.findByText('No audit logs found')).toBeInTheDocument();
  });

  test('saves private access settings and clears the submitted password', async () => {
    installApi({
      'PATCH /pools/pool-1': (url, options) => {
        expect(JSON.parse(options.body)).toEqual({ is_private: true, join_password: 'huddle42' });
        return response({ ...league, is_private: true });
      },
    });
    const user = userEvent.setup();
    render(<AdminPortal />);
    await screen.findByRole('heading', { name: 'Pool Management' });

    await user.click(screen.getByRole('radio', { name: /private/i }));
    await user.type(screen.getByLabelText('Join password'), 'huddle42');
    await user.click(screen.getByRole('button', { name: 'Save access settings' }));

    expect(await screen.findByText('Private access saved.')).toBeInTheDocument();
    expect(screen.getByLabelText('Join password')).toHaveValue('');
  });

  test('validates entry lookup and pick correction before calling the API', async () => {
    const user = userEvent.setup();
    render(<AdminPortal />);
    await screen.findByRole('heading', { name: 'Pool Management' });
    await user.click(screen.getByRole('button', { name: /entry management/i }));

    await user.click(screen.getByRole('button', { name: /search entries/i }));
    expect(screen.getByText('Please enter either username or entry name to search')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /correct pick/i }));
    expect(screen.getByText('Entry ID, week, and team are required.')).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  });

  test('shows scoped audit events and applies search filters', async () => {
    installApi({
      'GET /audit/?pool_id=pool-1&limit=500': () => response([{
        id: 'audit-1', action: 'UPDATE_PICK', user_email: 'admin@example.com',
        created_at: '2026-09-01T12:00:00Z', details: JSON.stringify({ description: 'Corrected week 2 pick' }),
      }]),
    });
    const user = userEvent.setup();
    render(<AdminPortal />);
    await screen.findByRole('heading', { name: 'Pool Management' });
    await user.click(screen.getByRole('button', { name: /audit log/i }));

    expect(await screen.findByText(/corrected week 2 pick/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeEnabled();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('pool_id=pool-1'),
      expect.any(Object),
    );
  });
});
