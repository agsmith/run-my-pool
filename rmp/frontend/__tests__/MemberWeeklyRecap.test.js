import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MemberWeeklyRecap from '../components/MemberWeeklyRecap';

process.env.NEXT_PUBLIC_API_URL = '';

describe('MemberWeeklyRecap', () => {
  beforeEach(() => localStorage.setItem('access_token', 'token'));
  afterEach(() => { jest.restoreAllMocks(); localStorage.clear(); });

  test('opts a member into weekly pool recaps', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ pool_id: 'pool-1', enabled: true }),
    }));
    const onChange = jest.fn();
    render(<MemberWeeklyRecap poolId="pool-1" enabled={false} onChange={onChange} />);

    await userEvent.click(screen.getByRole('checkbox'));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith('/pools/pool-1/member-recap-preference', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer token' },
      body: JSON.stringify({ enabled: true }),
    }));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  test('keeps the existing preference and explains an API failure', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: false,
      json: () => Promise.resolve({ detail: 'Service unavailable' }),
    }));
    const onChange = jest.fn();
    render(<MemberWeeklyRecap poolId="pool-1" enabled onChange={onChange} />);

    await userEvent.click(screen.getByRole('checkbox'));

    expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable');
    expect(onChange).not.toHaveBeenCalled();
  });
});
