import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import PoolMembersPage from '../pages/pool/[id]/members';

process.env.NEXT_PUBLIC_API_URL = '';
const mockRouter = { isReady: true, query: { id: 'pool-1' } };
jest.mock('next/router', () => ({ useRouter: () => mockRouter }));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);

const response = (data, ok = true) => Promise.resolve({
  ok,
  json: () => Promise.resolve(data),
});

describe('PoolMembersPage', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'token');
    global.fetch = jest.fn((url) => {
      if (String(url).endsWith('/members')) return response({
        pool_id: 'pool-1',
        total_users: 2,
        users: [
          { id: 'owner-1', email: 'owner@example.com', pool_role: 'Commissioner', entry_count: 2 },
          { id: 'member-1', email: 'member@example.com', pool_role: 'Member', entry_count: 1 },
        ],
      });
      if (String(url).endsWith('/is-admin')) return response({ has_admin_access: false });
      return response({ id: 'pool-1', name: 'Office Survivor', pool_type: 'survivor' });
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('shows every pool member with role and entry count', async () => {
    render(<PoolMembersPage />);

    expect(await screen.findByText('owner@example.com')).toBeInTheDocument();
    expect(screen.getByText('member@example.com')).toBeInTheDocument();
    expect(screen.getByText('Commissioner')).toBeInTheDocument();
    expect(screen.getAllByText('Member')).toHaveLength(1);
    expect(screen.getByText('2 members')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Members' })).toHaveAttribute('aria-current', 'page');
    expect(fetch).toHaveBeenCalledWith('/pools/pool-1/members', expect.objectContaining({
      headers: { Authorization: 'Bearer token' },
    }));
  });

  test('shows a scoped loading error', async () => {
    global.fetch = jest.fn((url) => String(url).endsWith('/members')
      ? response({ detail: 'League membership required' }, false)
      : response({ id: 'pool-1', name: 'Office Survivor', pool_type: 'survivor' }));

    render(<PoolMembersPage />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load pool members.');
  });
});
