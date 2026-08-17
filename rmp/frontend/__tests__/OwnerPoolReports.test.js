import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OwnerPoolReports from '../components/OwnerPoolReports';

beforeEach(() => {
  localStorage.setItem('access_token', 'token');
  global.fetch = jest.fn((url, options = {}) => {
    if (url.includes('owner-report-preview')) return Promise.resolve({
      ok: true, json: async () => ({ week: 4, members: 12, engaged_members: 9, total_entries: 20, remaining_entries: 15, weekly_entries_with_picks: 13, weekly_eligible_entries: 15, season_picks: 61 }),
    });
    if (options.method === 'PUT') return Promise.resolve({ ok: true, json: async () => ({ pool_id: 'pool-1', enabled: true, frequency: 'weekly', last_sent_at: null }) });
    return Promise.resolve({ ok: true, json: async () => ({ pool_id: 'pool-1', enabled: false, frequency: 'weekly', last_sent_at: null }) });
  });
});

afterEach(() => jest.restoreAllMocks());

test('previews owner value metrics and opts in to weekly email', async () => {
  const user = userEvent.setup();
  render(<OwnerPoolReports poolId="pool-1" />);
  expect(await screen.findByText('9/12')).toBeInTheDocument();
  expect(screen.getByText('15/20')).toBeInTheDocument();
  expect(screen.getByText('13/15')).toBeInTheDocument();
  await user.click(screen.getByRole('checkbox', { name: /email me weekly/i }));
  await waitFor(() => expect(screen.getByText('Weekly owner reports are on.')).toBeInTheDocument());
  expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining('owner-report-preference'), expect.objectContaining({
    method: 'PUT', body: JSON.stringify({ enabled: true, frequency: 'weekly' }),
  }));
});
