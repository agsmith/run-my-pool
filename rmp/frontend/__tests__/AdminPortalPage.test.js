import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
jest.mock('../components/OwnerPoolReports', () => function MockOwnerReports() {
  return <div>Weekly owner reports</div>;
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
    if (path.includes('/audit/filter-options')) return response({
      event_types: [], users: [], includes_system_events: false,
    });
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
    expect(screen.getByText('Weekly owner reports')).toBeInTheDocument();
    expect(screen.getByText('Pool lock settings')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Create Pool' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Modify Pool' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create Pool' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Modify Selected Pool' })).not.toBeInTheDocument();

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

  test('uses a focused member lookup and one contextual pool-lock action', async () => {
    installApi({
      'GET /admin/pools/pool-1/user-lock?email=player%40example.com': () => response({
        email: 'player@example.com', locked: false, reason: null,
      }),
      'PUT /admin/pools/pool-1/user-lock': (url, options) => {
        expect(JSON.parse(options.body)).toEqual({
          email: 'player@example.com', locked: true, reason: 'Payment pending',
        });
        return response({ email: 'player@example.com', locked: true, reason: 'Payment pending' });
      },
    });
    const user = userEvent.setup();
    render(<AdminPortal />);
    await screen.findByRole('heading', { name: 'Office Survivor' });
    await user.click(screen.getByRole('button', { name: /user management/i }));

    expect(screen.queryByRole('button', { name: 'Lock pool access' })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText('Member email'), 'player@example.com');
    await user.click(screen.getByRole('button', { name: 'Find member' }));

    expect(await screen.findByText('Active')).toBeInTheDocument();
    expect(screen.getByText('player@example.com')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Restore pool access' })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/Reason/), 'Payment pending');
    await user.click(screen.getByRole('button', { name: 'Lock pool access' }));

    expect(await screen.findByText('Locked')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Restore pool access' })).toBeInTheDocument();
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

  test('deletes only the current pool after owner confirmation', async () => {
    const confirm = jest.spyOn(window, 'confirm').mockReturnValue(true);
    installApi({
      'DELETE /pools/pool-1': () => response({ message: 'Pool deleted successfully' }),
    });
    const user = userEvent.setup();
    render(<AdminPortal />);
    await screen.findByRole('heading', { name: 'Pool Management' });

    expect(screen.queryByLabelText(/select pool to delete/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete this pool' }));

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('Delete "Office Survivor"?'));
    expect(fetch).toHaveBeenCalledWith('/pools/pool-1', expect.objectContaining({
      method: 'DELETE',
      headers: { Authorization: 'Bearer token' },
    }));
    expect(mockPush).toHaveBeenCalledWith('/dashboard?message=Pool deleted successfully');
  });

  test('does not delete the current pool when confirmation is cancelled', async () => {
    jest.spyOn(window, 'confirm').mockReturnValue(false);
    const user = userEvent.setup();
    render(<AdminPortal />);
    await screen.findByRole('heading', { name: 'Pool Management' });

    await user.click(screen.getByRole('button', { name: 'Delete this pool' }));

    expect(fetch.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);
    expect(mockPush).not.toHaveBeenCalled();
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
      'GET /audit/filter-options?pool_id=pool-1': () => response({
        event_types: ['CREATE_PICK', 'UPDATE_PICK'],
        users: [{ id: 'owner-1', email: 'owner@example.com' }],
        includes_system_events: true,
      }),
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

    await user.selectOptions(screen.getByLabelText('Audit event type'), 'UPDATE_PICK');
    await user.selectOptions(screen.getByLabelText('Audit user'), 'owner-1');
    fireEvent.change(screen.getByLabelText('From date and time'), {
      target: { value: '2026-09-01T08:30' },
    });
    fireEvent.change(screen.getByLabelText('To date and time'), {
      target: { value: '2026-09-01T12:45' },
    });
    await user.click(screen.getByRole('button', { name: 'Search Audit Log' }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/event_type=UPDATE_PICK/),
      expect.any(Object),
    ));
    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/user_id=owner-1/),
      expect.any(Object),
    );
    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/date_from=/),
      expect.any(Object),
    );
    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/date_to=/),
      expect.any(Object),
    );
  });
});
