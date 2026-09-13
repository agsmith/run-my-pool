import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AdminPickCorrection from '../components/AdminPickCorrection';

const picks = [
  { id: 'pick-a', entry_name: 'First entry', week: 1, team: 'SEA', game_id: 10 },
  { id: 'pick-b', entry_name: 'First entry', week: 1, team: 'BUF', game_id: 11 },
];
beforeEach(() => {
  process.env.NEXT_PUBLIC_API_URL = '';
  global.fetch = jest.fn(async (url, options) => {
    let data;
    if (url.endsWith('/users-overview')) data = { users: [{ id: 'u1', email: 'one@example.com' }, { id: 'u2', email: 'two@example.com' }] };
    else if (url.endsWith('/teams/')) data = [{ id: 1, abbrv: 'SEA' }, { id: 2, abbrv: 'BUF' }, { id: 3, abbrv: 'MIA' }];
    else if (url.includes('/users/u1/')) data = picks;
    else if (url.includes('/users/u2/')) data = [];
    else if (options.method === 'PATCH') data = { id: 'pick-b', team: 'MIA', week: 1 };
    else throw new Error('Unexpected request');
    return { ok: true, json: async () => data };
  });
});
test('corrects the exact pick in a multi-game week and shows the updated current team', async () => {
  const user = userEvent.setup(); render(<AdminPickCorrection poolId="pool" />);
  await screen.findByRole('option', { name: 'one@example.com' });
  await user.selectOptions(screen.getByLabelText('Username'), 'u1');
  await screen.findByRole('option', { name: /First entry.*Week 1.*BUF/ });
  await user.selectOptions(screen.getByLabelText('User’s pick'), 'pick-b');
  expect(screen.getByText('Current pick: BUF')).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Modified pick'), 'MIA');
  await user.type(screen.getByLabelText('Reason for correction'), 'Requested correction');
  await user.click(screen.getByRole('button', { name: 'Correct Pick' }));
  expect(fetch).toHaveBeenCalledWith('/admin/pools/pool/picks/pick-b', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ team: 'MIA', reason: 'Requested correction' }) }));
  await screen.findByText('Current pick: MIA');
  expect(screen.getByRole('status')).toHaveTextContent('BUF corrected to MIA');
});
test('changing users clears the previous selection and cannot submit their pick', async () => {
  const user = userEvent.setup(); render(<AdminPickCorrection poolId="pool" />);
  await screen.findByRole('option', { name: 'one@example.com' });
  await user.selectOptions(screen.getByLabelText('Username'), 'u1');
  await screen.findByRole('option', { name: /First entry.*Week 1.*BUF/ });
  await user.selectOptions(screen.getByLabelText('User’s pick'), 'pick-b');
  await user.selectOptions(screen.getByLabelText('Modified pick'), 'MIA');
  await user.selectOptions(screen.getByLabelText('Username'), 'u2');
  await screen.findByText('No saved picks for this user in this pool.');
  expect(screen.getByRole('button', { name: 'Correct Pick' })).toBeDisabled();
  expect(screen.getByText('Current pick: Select a pick above')).toBeInTheDocument();
});
test('reports a rejected correction without changing the current pick', async () => {
  const user = userEvent.setup(); render(<AdminPickCorrection poolId="pool" />);
  await screen.findByRole('option', { name: 'one@example.com' });
  await user.selectOptions(screen.getByLabelText('Username'), 'u1');
  await screen.findByRole('option', { name: /First entry.*Week 1.*BUF/ });
  await user.selectOptions(screen.getByLabelText('User’s pick'), 'pick-b');
  await user.selectOptions(screen.getByLabelText('Modified pick'), 'MIA');
  fetch.mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'Selected team is not playing in this game' }) });
  await user.click(screen.getByRole('button', { name: 'Correct Pick' }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Selected team is not playing in this game'));
  expect(screen.getByText('Current pick: BUF')).toBeInTheDocument();
});
