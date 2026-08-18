import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
          { id: 'member-1', display_name: 'member', pool_role: 'Member', entry_count: 4, remaining_entry_count: 3, total_entry_count: 4 },
          { id: 'owner-1', display_name: 'owner', pool_role: 'Commissioner', entry_count: 3, remaining_entry_count: 1, total_entry_count: 3 },
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

  test('defaults to alphabetical order and sorts by remaining picks', async () => {
    const user = userEvent.setup();
    render(<PoolMembersPage />);

    expect(await screen.findByText('owner')).toBeInTheDocument();
    expect(screen.getByText('member')).toBeInTheDocument();
    expect(screen.queryByText(/@example\.com/)).not.toBeInTheDocument();
    expect(screen.getByText('Commissioner')).toBeInTheDocument();
    expect(screen.getAllByText('Member')).toHaveLength(1);
    expect(screen.getByText('2 members')).toBeInTheDocument();
    expect(screen.getByLabelText('3 of 4 entries remaining')).toHaveTextContent('3/4');
    expect(screen.getByLabelText('1 of 3 entries remaining')).toHaveTextContent('1/3');
    let memberCards = screen.getByRole('region', { name: 'Pool members' }).querySelectorAll('.pool-member-card');
    expect(memberCards[0]).toHaveTextContent('member');
    expect(memberCards[1]).toHaveTextContent('owner');
    await user.click(screen.getByRole('button', { name: 'Picks Remaining' }));
    memberCards = screen.getByRole('region', { name: 'Pool members' }).querySelectorAll('.pool-member-card');
    expect(memberCards[0]).toHaveTextContent('member');
    expect(memberCards[1]).toHaveTextContent('owner');
    await user.click(screen.getByRole('button', { name: 'Picks Remaining High–Low' }));
    memberCards = screen.getByRole('region', { name: 'Pool members' }).querySelectorAll('.pool-member-card');
    expect(memberCards[0]).toHaveTextContent('owner');
    expect(memberCards[1]).toHaveTextContent('member');
    await user.click(screen.getByRole('button', { name: 'Name' }));
    memberCards = screen.getByRole('region', { name: 'Pool members' }).querySelectorAll('.pool-member-card');
    expect(memberCards[0]).toHaveTextContent('member');
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
