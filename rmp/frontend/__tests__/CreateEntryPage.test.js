import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CreateEntry from '../pages/pool/[id]/entries/create';

const mockPush = jest.fn();
jest.mock('next/router', () => ({
  useRouter: () => ({ isReady: true, query: { id: 'pickem-pool' }, push: mockPush }),
}));
jest.mock('../components/ProtectedRoute', () => ({ children }) => children);

describe('CreateEntry', () => {
  beforeEach(() => {
    mockPush.mockClear();
    localStorage.setItem('access_token', 'token');
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'pickem-pool', name: 'Pick Em', pool_type: 'pickem' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'entry-1' }) });
  });

  test('takes a new Pick Em entry to the Pick Em board', async () => {
    const user = userEvent.setup();
    render(<CreateEntry />);

    await screen.findByRole('heading', { name: /for Pick Em/i });
    await user.type(screen.getByPlaceholderText(/enter a name for your entry/i), 'My Picks');
    await user.click(screen.getByRole('button', { name: /^create entry$/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith(
      '/pool/pickem-pool/pickem?message=Entry "My Picks" created successfully!',
    ));
  });
});
