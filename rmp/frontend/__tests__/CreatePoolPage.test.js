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
    fetch
      .mockResolvedValueOnce({ ok: true, json: async () => [] })
      .mockResolvedValueOnce({
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
    await user.click(screen.getByRole('button', { name: /^create pool$/i }));

    expect(await screen.findByText(/already in use/i)).toBeInTheDocument();
    const suggestion = screen.getByRole('button', { name: /use office pool 2026/i });
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

  test('redirects the legacy create-league route to the splash page', () => {
    expect(getLegacyCreateServerSideProps()).toEqual({
      redirect: { destination: '/', permanent: false },
    });
  });
});
