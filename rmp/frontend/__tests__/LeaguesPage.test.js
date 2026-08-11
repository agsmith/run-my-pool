import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Leagues from '../pages/leagues';

const mockPush = jest.fn();
jest.mock('next/router', () => ({
  useRouter: () => ({ push: mockPush }),
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
    expect(await screen.findByRole('button', { name: /open pool/i })).toBeInTheDocument();
  });

  test('requires and submits a password for a private pool', async () => {
    global.fetch.mockImplementationOnce(() => response({ message: 'Pool joined successfully' }));
    const user = userEvent.setup();
    render(<Leagues />);
    await screen.findByRole('heading', { name: 'Private Pool' });

    const privateCard = screen.getByRole('heading', { name: 'Private Pool' }).closest('article');
    await user.click(privateCard.querySelector('button'));
    const password = screen.getByLabelText(/pool password/i);
    expect(password).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledTimes(2);

    await user.type(password, 'huddle42');
    await user.click(screen.getByRole('button', { name: /unlock & join/i }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
    expect(JSON.parse(global.fetch.mock.calls[2][1].body)).toEqual({ password: 'huddle42' });
  });

  test('shows a private-password error returned by the API', async () => {
    global.fetch.mockImplementationOnce(() => response({ detail: 'Invalid pool password' }, false));
    const user = userEvent.setup();
    render(<Leagues />);
    await screen.findByRole('heading', { name: 'Private Pool' });
    const privateCard = screen.getByRole('heading', { name: 'Private Pool' }).closest('article');
    await user.click(privateCard.querySelector('button'));
    await user.type(screen.getByLabelText(/pool password/i), 'incorrect');
    await user.click(screen.getByRole('button', { name: /unlock & join/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid pool password');
  });
});
