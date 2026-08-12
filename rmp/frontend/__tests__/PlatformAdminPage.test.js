import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Admin from '../pages/admin';

process.env.NEXT_PUBLIC_API_URL = '';
const mockUser = { id: 'admin-1', email: 'agsmith11@gmail.com', role: 'SUPER_ADMIN' };
jest.mock('../components/SuperAdminRoute', () => ({ children }) => children);
jest.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: mockUser }) }));

const summary = {
  total: 2, active: 1, locked: 1, pool_admins: 1, super_admins: 1, unassigned: 1,
  users: [
    { id: 'user-1', email: 'active@example.com', role: 'USER', is_active: true, pool_count: 0, created_at: '2026-08-01T12:00:00Z' },
    { id: 'user-2', email: 'locked@example.com', role: 'POOL_ADMIN', is_active: false, pool_count: 2, created_at: null },
  ],
};

describe('platform admin dashboard', () => {
  beforeEach(() => localStorage.setItem('access_token', 'token'));
  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('shows scoped user totals, roles, and account status', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => summary });
    render(<Admin />);

    expect(await screen.findByText('active@example.com')).toBeInTheDocument();
    expect(screen.getByText('locked@example.com')).toBeInTheDocument();
    expect(screen.getByText('Member')).toBeInTheDocument();
    expect(screen.getByText('Pool admin')).toBeInTheDocument();
    expect(screen.getByText('Locked')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'ALL USERS' })).toBeInTheDocument();
  });

  test('trims and submits an email search', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => summary });
    const user = userEvent.setup();
    render(<Admin />);
    await screen.findByText('active@example.com');

    await user.type(screen.getByLabelText('Search by email'), '  active@example.com  ');
    await user.click(screen.getByRole('button', { name: 'Search' }));

    expect(fetch).toHaveBeenLastCalledWith(
      '/users/admin-dashboard?limit=500&search=active%40example.com',
      expect.any(Object),
    );
  });

  test('surfaces API authorization errors', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'Administrator access required' }),
    });
    render(<Admin />);

    expect(await screen.findByText('Administrator access required')).toBeInTheDocument();
    expect(screen.getByText('No records match that search.')).toBeInTheDocument();
  });

  test('filters users without a pool and can deactivate an account', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => summary });
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();
    render(<Admin />);
    await screen.findByText('active@example.com');

    await user.click(screen.getByRole('button', { name: 'Not in a pool (1)' }));
    expect(fetch).toHaveBeenLastCalledWith(
      '/users/admin-dashboard?limit=500&unassigned_only=true',
      expect.any(Object),
    );

    await user.click(screen.getByRole('button', { name: 'Deactivate' }));
    expect(fetch).toHaveBeenCalledWith(
      '/users/user-1/status?active=false',
      expect.objectContaining({ method: 'PATCH' }),
    );
  });

  test('can grant super admin access to a support user', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => summary });
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();
    render(<Admin />);
    await screen.findByText('active@example.com');

    await user.click(screen.getAllByRole('button', { name: 'Grant super admin' })[0]);

    expect(fetch).toHaveBeenCalledWith(
      '/users/user-1/super-admin?enabled=true',
      expect.objectContaining({ method: 'PATCH' }),
    );
  });
});
