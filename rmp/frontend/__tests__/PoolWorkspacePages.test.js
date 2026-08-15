import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PoolDetail from '../pages/pool/[id]';
import MatchupsPage from '../pages/pool/[id]/matchups';
import MessageBoard from '../pages/pool/[id]/messages';

const mockTrackLifecycleEvent = jest.fn();
jest.mock('../lib/lifecycleAnalytics', () => ({
  trackLifecycleEvent: (...args) => mockTrackLifecycleEvent(...args),
}));

process.env.NEXT_PUBLIC_API_URL = '';
const mockPush = jest.fn();
const mockBack = jest.fn();
const mockUser = { id: 'user-1', email: 'player@example.com' };
const mockRouter = { isReady: true, query: { id: 'pool-1' }, push: mockPush, back: mockBack };
jest.mock('next/router', () => ({ useRouter: () => mockRouter }));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);
jest.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: mockUser }) }));

const response = (data, ok = true, status = ok ? 200 : 400) => Promise.resolve({
  ok, status, json: () => Promise.resolve(data),
});
const pool = {
  id: 'pool-1', name: 'Office Survivor', owner_id: 'user-1', description: 'Make it through the season',
  is_private: true, lock_day_of_week: 6, lock_time_of_day: '13:00:00', lock_timezone: 'America/New_York',
};
const activitySummary = {
  pool_type: 'survivor', entries_remaining: 2, total_entries: 3,
  week: 5, week_selections: 1, week_selection_total: 2,
};

describe('pool workspace pages', () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockBack.mockReset();
    mockRouter.query = { id: 'pool-1' };
    mockTrackLifecycleEvent.mockClear();
    localStorage.setItem('access_token', 'token');
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('owner sees commissioner controls and can delete after confirmation', async () => {
    global.confirm = jest.fn(() => true);
    global.fetch = jest.fn((url, options = {}) => {
      if (String(url).endsWith('/is-admin')) return response({ is_owner: true, is_admin: true, has_admin_access: true });
      if (String(url).endsWith('/activity-summary')) return response(activitySummary);
      if (!options.method) return response(pool);
      if (options.method === 'DELETE') return response({ message: 'deleted' });
      throw new Error(`Unexpected request ${url}`);
    });
    const user = userEvent.setup();
    render(<PoolDetail />);

    expect(await screen.findByRole('heading', { name: 'Office Survivor' })).toBeInTheDocument();
    expect(screen.getAllByText('Commissioner')).toHaveLength(2);
    expect(screen.getByText('Private · Password required')).toBeInTheDocument();
    expect(screen.getByText('Sunday at 1:00 PM · America/New_York')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'My Entries' })).toHaveLength(1);
    expect(screen.getAllByText('My Entries')).toHaveLength(2);
    expect(screen.getAllByText('Weekly Matchups')).toHaveLength(2);
    expect(screen.getAllByText('Forum')).toHaveLength(2);
    await user.click(screen.getByRole('button', { name: 'Delete Pool' }));

    expect(global.confirm).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith('/dashboard?message=Pool deleted successfully');
  });

  test('shows the launch checklist to the owner immediately after creation', async () => {
    mockRouter.query = { id: 'pool-1', launched: '1' };
    global.fetch = jest.fn((url, options = {}) => {
      if (String(url).endsWith('/is-admin')) return response({ is_owner: true, is_admin: true, has_admin_access: true });
      if (String(url).endsWith('/activity-summary')) return response(activitySummary);
      if (String(url).endsWith('/invite-email') && options.method === 'POST') return response({ message: 'Invitation email sent' });
      return response(pool);
    });
    const user = userEvent.setup();

    render(<PoolDetail />);

    expect(await screen.findByRole('region', { name: /pool launch checklist/i })).toBeInTheDocument();
    expect(screen.getByText(/1 of 4 launch steps complete/i)).toBeInTheDocument();
    expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('pool_launch_checklist_view', { page: 'pool_home' });
    await user.type(screen.getByLabelText(/or send by email/i), 'player@example.com');
    await user.click(screen.getByRole('button', { name: /send invite/i }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      '/pools/pool-1/invite-email',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ email: 'player@example.com' }) }),
    ));
  });

  test('shows the current user’s pool administrator role and controls', async () => {
    global.fetch = jest.fn((url) => {
      if (String(url).endsWith('/is-admin')) return response({ is_owner: false, is_admin: true, has_admin_access: true });
      if (String(url).endsWith('/activity-summary')) return response(activitySummary);
      return response({ ...pool, owner_id: 'another-user' });
    });

    render(<PoolDetail />);

    expect(await screen.findByText('Admin')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Commissioner Settings' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete Pool' })).not.toBeInTheDocument();
  });

  test('welcomes a newly joined member and opens first-entry creation', async () => {
    mockRouter.query = { id: 'pool-1', joined: '1' };
    global.fetch = jest.fn((url) => {
      if (String(url).endsWith('/is-admin')) return response({ is_owner: false, is_admin: false, has_admin_access: false });
      if (String(url).endsWith('/activity-summary')) return response({ ...activitySummary, entries_remaining: 0, total_entries: 0, week_selections: 0, week_selection_total: 0 });
      return response({ ...pool, owner_id: 'owner-2', pool_type: 'survivor' });
    });
    const user = userEvent.setup();
    render(<PoolDetail />);

    expect(await screen.findByRole('region', { name: /pool membership welcome/i })).toBeInTheDocument();
    expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('member_onboarding_view', { page: 'pool_home' });
    expect(screen.getByRole('heading', { name: 'Week 5 Action Center' })).toBeInTheDocument();
    await user.click(
      screen.getByRole('region', { name: /pool membership welcome/i })
        .querySelector('button'),
    );
    expect(mockPush).toHaveBeenCalledWith('/pool/pool-1/entries/create');
  });

  test('renders official, live, and pending matchup lines and changes week', async () => {
    const games = [
      {
        game_id: 1, start_time: '2026-09-13T17:00:00Z',
        away_team: { abbrv: 'BUF', name: 'Buffalo Bills' }, home_team: { abbrv: 'MIA', name: 'Miami Dolphins' },
        official_line: { details: 'BUF -3', provider: 'book' }, live_line: null,
      },
      {
        game_id: 2, start_time: '2026-09-13T20:00:00Z',
        away_team: { abbrv: 'KC', name: 'Kansas City Chiefs' }, home_team: { abbrv: 'DEN', name: 'Denver Broncos' },
        official_line: null, live_line: { details: 'KC -2', provider: 'ESPN' },
      },
      {
        game_id: 3, start_time: '2026-09-14T00:00:00Z',
        away_team: { abbrv: 'NYG', name: 'New York Giants' }, home_team: { abbrv: 'DAL', name: 'Dallas Cowboys' },
        official_line: null, live_line: null,
      },
    ];
    global.fetch = jest.fn((url) => {
      const path = String(url);
      if (path.endsWith('/pools/pool-1')) return response(pool);
      if (path.includes('/schedule/week/1/')) return response(games);
      if (path.includes('/schedule/week/2/')) return response([]);
      throw new Error(`Unexpected request ${path}`);
    });
    const user = userEvent.setup();
    render(<MatchupsPage />);

    expect(await screen.findByText('BUF -3')).toBeInTheDocument();
    expect(screen.getByTitle('BUF')).toHaveAttribute('src', '/nfl/buf.svg');
    expect(screen.getByText('Official line at lock')).toBeInTheDocument();
    expect(screen.getByText('Live · ESPN')).toBeInTheDocument();
    expect(screen.getByText('Line pending')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Next →' }));
    expect(await screen.findByText('No matchups are scheduled for this week.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Week 2 matchups' })).toBeInTheDocument();
  });

  test('posts and deletes only the current user’s message', async () => {
    global.confirm = jest.fn(() => true);
    const initial = [
      { id: 'mine', user_id: 'user-1', user_email: 'player@example.com', message: 'My update', created_at: '2026-09-01T12:00:00Z' },
      { id: 'other', user_id: 'user-2', user_email: 'other@example.com', message: 'Other update', created_at: '2026-09-01T13:00:00Z' },
    ];
    global.fetch = jest.fn((url, options = {}) => {
      const path = String(url);
      if (path.endsWith('/pools/pool-1')) return response(pool);
      if (path.endsWith('/messages/pool/pool-1') && !options.method) return response(initial);
      if (path.endsWith('/messages/pool/pool-1') && options.method === 'POST') {
        return response({ id: 'new', user_id: 'user-1', user_email: 'player@example.com', message: 'Sunday reminder', created_at: '2026-09-02T12:00:00Z' });
      }
      if (path.endsWith('/messages/mine') && options.method === 'DELETE') return response({ message: 'deleted' });
      throw new Error(`Unexpected request ${path}`);
    });
    const user = userEvent.setup();
    render(<MessageBoard />);

    expect(await screen.findByText('My update')).toBeInTheDocument();
    expect(screen.getByText('Other update')).toBeInTheDocument();
    expect(screen.getByText('player@example.com').closest('.message-card__author')).toBeInTheDocument();
    expect(screen.getByText('other@example.com')).toHaveClass('message-card__author');
    expect(screen.getAllByTitle('Delete your message')).toHaveLength(1);

    await user.type(screen.getByPlaceholderText(/share something/i), 'Sunday reminder');
    await user.click(screen.getByRole('button', { name: 'Post Message' }));
    expect(await screen.findByText('Sunday reminder')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/share something/i)).toHaveValue('');

    await user.click(screen.getAllByTitle('Delete your message').find((button) => button.closest('article').textContent.includes('My update')));
    await waitFor(() => expect(screen.queryByText('My update')).not.toBeInTheDocument());
  });

  test('shows a membership-specific message-board denial', async () => {
    global.fetch = jest.fn((url) => {
      const path = String(url);
      if (path.endsWith('/pools/pool-1')) return response(pool);
      if (path.endsWith('/messages/pool/pool-1')) return response({ detail: 'forbidden' }, false, 403);
      throw new Error(`Unexpected request ${path}`);
    });
    render(<MessageBoard />);

    expect(await screen.findByText('You must be a member of this pool to view messages')).toBeInTheDocument();
  });
});
