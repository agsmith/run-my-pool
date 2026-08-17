import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Leagues from '../pages/leagues';

const mockPush = jest.fn();
let mockQuery = {};
jest.mock('next/router', () => ({
  useRouter: () => ({ push: mockPush, query: mockQuery }),
}));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);

const pools = [
  { id: 'public-pool', name: 'Public Pool', description: 'Open access', is_private: false },
  { id: 'private-pool', name: 'Private Pool', description: 'Password access', is_private: true },
];

function response(data, ok = true) {
  return Promise.resolve({ ok, json: () => Promise.resolve(data) });
}

beforeEach(() => {
  mockPush.mockReset();
  mockQuery = {};
  window.localStorage.setItem('access_token', 'test-token');
  global.fetch = jest.fn()
    .mockImplementationOnce(() => response(pools))
    .mockImplementationOnce(() => response([]));
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('Join a Pool', () => {
  test('loads real public and private pools', async () => {
    render(<Leagues />);
    expect(await screen.findByRole('heading', { name: 'Public Pool' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Private Pool' })).toBeInTheDocument();
    expect(screen.getByText('Public')).toBeInTheDocument();
    expect(screen.getByText('Private')).toBeInTheDocument();
    const search = screen.getByRole('searchbox', { name: 'Search pools' });
    expect(search).toHaveValue('');
    expect(search).toHaveAttribute('autocomplete', 'off');
    expect(search).toHaveAttribute('readonly');
    expect(screen.queryByRole('button', { name: /create.*pool/i })).not.toBeInTheDocument();
  });

  test('activates search only after user interaction to prevent credential autofill', async () => {
    const user = userEvent.setup();
    render(<Leagues />);
    await screen.findByRole('heading', { name: 'Public Pool' });
    const search = screen.getByRole('searchbox', { name: 'Search pools' });

    await user.click(search);
    await user.type(search, 'Private');

    expect(search).not.toHaveAttribute('readonly');
    expect(search).toHaveValue('Private');
    expect(screen.queryByRole('heading', { name: 'Public Pool' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Private Pool' })).toBeInTheDocument();
  });

  test('shows memberships in My Pools and excludes pools not joined', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() => response(pools))
      .mockImplementationOnce(() => response([pools[1]]));
    const user = userEvent.setup();
    render(<Leagues />);
    await screen.findByRole('heading', { name: 'Public Pool' });

    await user.click(screen.getByRole('button', { name: /my pools/i }));
    expect(screen.getByRole('heading', { name: 'Private Pool' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Public Pool' })).not.toBeInTheDocument();
  });

  test('keeps Browse Pools available when memberships fail to load', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() => response(pools))
      .mockImplementationOnce(() => response({ detail: 'Failed' }, false));
    const user = userEvent.setup();
    render(<Leagues />);

    expect(await screen.findByRole('heading', { name: 'Public Pool' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Private Pool' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /my pools/i }));
    expect(screen.getByText('Unable to load your pool memberships. Please try again.')).toBeInTheDocument();
  });

  test('joins a public pool without requesting a password', async () => {
    global.fetch.mockImplementationOnce(() => response({ message: 'Pool joined successfully' }));
    const user = userEvent.setup();
    render(<Leagues />);
    await screen.findByRole('heading', { name: 'Public Pool' });

    const publicCard = screen.getByRole('heading', { name: 'Public Pool' }).closest('article');
    await user.click(publicCard.querySelector('button'));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
    expect(JSON.parse(global.fetch.mock.calls[2][1].body)).toEqual({ password: null });
    expect(mockPush).toHaveBeenCalledWith('/pool/public-pool?joined=1');
  });

  test('requires and submits a password for a private pool', async () => {
    global.fetch.mockImplementationOnce(() => response({ message: 'Pool joined successfully' }));
    const user = userEvent.setup();
    render(<Leagues />);
    await screen.findByRole('heading', { name: 'Private Pool' });

    const privateCard = screen.getByRole('heading', { name: 'Private Pool' }).closest('article');
    await user.click(privateCard.querySelector('button'));
    const password = screen.getByLabelText(/^pool join code$/i);
    expect(password).toBeInTheDocument();
    expect(password).toHaveAttribute('type', 'text');
    expect(password).toHaveAttribute('autocomplete', 'one-time-code');
    expect(password).toHaveAttribute('name', 'pool-join-code-private-pool');
    expect(global.fetch).toHaveBeenCalledTimes(2);

    await user.type(password, 'huddle42');
    await user.click(screen.getByRole('button', { name: /submit join code/i }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
    expect(JSON.parse(global.fetch.mock.calls[2][1].body)).toEqual({ password: 'huddle42' });
    expect(mockPush).toHaveBeenCalledWith('/pool/private-pool?joined=1');
  });

  test('loads a shared private pool that is absent from public discovery', async () => {
    mockQuery = { invite: 'invited-private-pool' };
    const invitedPool = {
      id: 'invited-private-pool',
      name: 'Invite Only Pool',
      description: 'Shared by the commish',
      is_private: true,
    };
    global.fetch = jest.fn()
      .mockImplementationOnce(() => response([pools[0]]))
      .mockImplementationOnce(() => response([]))
      .mockImplementationOnce(() => response(invitedPool));

    render(<Leagues />);

    expect(await screen.findByRole('heading', { name: 'Invite Only Pool' })).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/pools/invite/invited-private-pool'),
      expect.objectContaining({ cache: 'no-store' }),
    );
  });

  test('shows a private-password error returned by the API', async () => {
    global.fetch.mockImplementationOnce(() => response({ detail: 'Invalid pool password' }, false));
    const user = userEvent.setup();
    render(<Leagues />);
    await screen.findByRole('heading', { name: 'Private Pool' });
    const privateCard = screen.getByRole('heading', { name: 'Private Pool' }).closest('article');
    await user.click(privateCard.querySelector('button'));
    await user.type(screen.getByLabelText(/^pool join code$/i), 'incorrect');
    await user.click(screen.getByRole('button', { name: /submit join code/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid pool password');
  });

  test('removes the join button after league registration closes', async () => {
    const closedPool = { ...pools[0], id: 'closed-pool', name: 'Closed Pool', join_lock_time: '2020-01-01T00:00:00' };
    global.fetch = jest.fn()
      .mockImplementationOnce(() => response([closedPool]))
      .mockImplementationOnce(() => response([]));

    render(<Leagues />);
    const card = (await screen.findByRole('heading', { name: 'Closed Pool' })).closest('article');
    expect(card).toHaveTextContent('Registration closed');
    expect(card.querySelector('button')).toBeNull();
  });

  test('shows free Squares boards without allowing online joining', async () => {
    const ownerManaged = { id: 'free-squares', name: 'Owner Squares', pool_type: 'squares', plan: 'free', is_private: false };
    global.fetch = jest.fn()
      .mockImplementationOnce(() => response([ownerManaged]))
      .mockImplementationOnce(() => response([]));

    render(<Leagues />);

    const card = (await screen.findByRole('heading', { name: 'Owner Squares' })).closest('article');
    expect(card).toHaveTextContent('Owner-managed');
    expect(card).toHaveTextContent('not open for online joining');
    expect(card.querySelector('button')).toBeNull();
  });
});
