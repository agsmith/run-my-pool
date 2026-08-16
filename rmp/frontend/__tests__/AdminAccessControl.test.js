import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import AdminAccessControl from '../components/AdminAccessControl';

describe('AdminAccessControl', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token');
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('grants league admin access and refreshes the overview', async () => {
    const onChanged = jest.fn();
    fetch.mockResolvedValue({ ok: true, json: async () => ({ email: 'member@example.com', is_admin: true, changed: true }) });
    render(<AdminAccessControl poolId="pool-1" onChanged={onChanged} />);

    fireEvent.change(screen.getByLabelText('Member email'), { target: { value: 'member@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Grant admin access' }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/admin/pools/pool-1/admins'),
      expect.objectContaining({ method: 'PUT', body: JSON.stringify({ email: 'member@example.com' }) }),
    ));
    expect(await screen.findByText('Pool admin access granted to member@example.com.')).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  test('revokes only league admin access', async () => {
    fetch.mockResolvedValue({ ok: true, json: async () => ({ email: 'member@example.com', is_admin: false, changed: true }) });
    render(<AdminAccessControl poolId="pool-1" onChanged={() => {}} />);

    fireEvent.change(screen.getByLabelText('Member email'), { target: { value: 'member@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Revoke admin access' }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/admin/pools/pool-1/admins?email=member%40example.com'),
      expect.objectContaining({ method: 'DELETE' }),
    ));
    expect(await screen.findByText('Pool admin access revoked from member@example.com.')).toBeInTheDocument();
  });

  test('shows backend validation errors', async () => {
    fetch.mockResolvedValue({ ok: false, json: async () => ({ detail: 'User must join the pool before becoming an administrator' }) });
    render(<AdminAccessControl poolId="pool-1" />);

    fireEvent.change(screen.getByLabelText('Member email'), { target: { value: 'outsider@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Grant admin access' }));

    expect(await screen.findByText('User must join the pool before becoming an administrator')).toBeInTheDocument();
  });
});
