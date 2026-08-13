import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CreatePool, { getServerSideProps } from '../pages/create-pool';
import { getServerSideProps as getLegacyCreateServerSideProps } from '../pages/create-league';

const mockPush = jest.fn();

jest.mock('next/router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock('../components/ProtectedRoute', () => ({ children }) => children);

describe('CreatePool', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
    mockPush.mockClear();
    localStorage.setItem('access_token', 'test-token');
  });

  test('shows unique name suggestions and lets the owner select one', async () => {
    const user = userEvent.setup();
    fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: {
            code: 'league_name_taken',
            message: 'That league name is already in use. Choose a unique name.',
            suggestions: ['Office Pool 2026', 'Office Pool Survivor', 'Office Pool 2'],
          },
        }),
      });

    render(<CreatePool />);
    await user.type(screen.getByPlaceholderText(/enter pool name/i), 'Office Pool');
    await user.click(screen.getByRole('button', { name: /create survivor pool/i }));

    expect(await screen.findByText(/already in use/i)).toBeInTheDocument();
    const suggestion = screen.getByRole('button', { name: /office pool 2026/i });
    expect(suggestion).toBeInTheDocument();

    await user.click(suggestion);
    expect(screen.getByPlaceholderText(/enter pool name/i)).toHaveValue('Office Pool 2026');
    await waitFor(() => expect(screen.queryByText(/already in use/i)).not.toBeInTheDocument());
  });

  test('only allows the pool creation page to be entered from the splash page', () => {
    expect(getServerSideProps({ query: {} })).toEqual({
      redirect: { destination: '/', permanent: false },
    });
    expect(getServerSideProps({ query: { source: 'splash' } })).toEqual({ props: {} });
  });

  test('lets the commissioner choose Pick Em and sends the pool type', async () => {
    const user = userEvent.setup();
    fetch.mockResolvedValue({ ok: true, json: async () => ({ id: 'pickem-pool' }) });
    render(<CreatePool />);

    await user.click(screen.getByRole('radio', { name: /pick ’em/i }));
    expect(screen.getByText(/missing games receive no selection and no point/i)).toBeInTheDocument();
    expect(screen.queryByText(/pick losers/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/auto-pick strategy/i)).not.toBeInTheDocument();
    await user.type(screen.getByPlaceholderText(/enter pool name/i), 'Office Pick Em');
    await user.click(screen.getByRole('button', { name: /create pick ’em pool/i }));

    const createCall = fetch.mock.calls.find(([url, options]) => String(url).endsWith('/pools/create') && options?.method === 'POST');
    expect(JSON.parse(createCall[1].body)).toEqual(expect.objectContaining({
      pool_type: 'pickem',
      lock_day_of_week: 6,
      lock_time_of_day: '13:00:00',
      lock_timezone: 'America/New_York',
      rule_values: [],
    }));
    expect(mockPush).toHaveBeenCalledWith('/pool/pickem-pool?launched=1');
  });

  test('defaults Pick Em to all games and allows a fixed weekly slate', async () => {
    const user = userEvent.setup();
    fetch.mockResolvedValue({ ok: true, json: async () => ({ id: 'five-game-pool' }) });
    render(<CreatePool />);

    await user.click(screen.getByRole('radio', { name: /pick ’em/i }));
    const gameCount = screen.getByRole('combobox', { name: /required games per week/i });
    expect(gameCount).toHaveValue('all');
    expect(screen.getByText(/target automatically matches/i)).toBeInTheDocument();

    await user.selectOptions(gameCount, '5');
    expect(screen.getByText(/up to 5 selections/i)).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText(/enter pool name/i), 'Five Game Pick Em');
    await user.click(screen.getByRole('button', { name: /create pick ’em pool/i }));

    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(expect.objectContaining({
      pool_type: 'pickem',
      pickem_games_per_week: 5,
    }));
  });

  test('sends supported Survivor settings and a shareable private join code', async () => {
    const user = userEvent.setup();
    fetch.mockResolvedValue({ ok: true, json: async () => ({ id: 'survivor-pool' }) });
    render(<CreatePool />);

    expect(screen.getByText(/entries without a selection receive the best available automatic pick/i)).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText(/enter pool name/i), 'Family Survivor');
    await user.selectOptions(screen.getByLabelText('Lock day'), '3');
    await user.selectOptions(screen.getByLabelText('Lock time zone'), 'America/Chicago');
    await user.click(screen.getByRole('radio', { name: /private/i }));
    const joinCode = screen.getByPlaceholderText(/at least 6 characters/i);
    expect(joinCode).toHaveAttribute('type', 'text');
    await user.type(joinCode, 'huddle42');
    await user.click(screen.getByRole('button', { name: /create survivor pool/i }));

    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(expect.objectContaining({
      pool_type: 'survivor', lock_day_of_week: 3, lock_timezone: 'America/Chicago',
      is_private: true, join_password: 'huddle42',
    }));
  });

  test('redirects the legacy create-league route to the splash page', () => {
    expect(getLegacyCreateServerSideProps()).toEqual({
      redirect: { destination: '/', permanent: false },
    });
  });
});
