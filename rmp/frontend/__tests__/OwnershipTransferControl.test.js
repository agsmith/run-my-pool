import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import OwnershipTransferControl from '../components/OwnershipTransferControl';

describe('OwnershipTransferControl', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token');
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('requires the exact league name before transferring ownership', async () => {
    const onTransferred = jest.fn();
    fetch.mockResolvedValue({ ok: true, json: async () => ({ owner_email: 'new@example.com' }) });
    render(<OwnershipTransferControl poolId="pool-1" poolName="Sunday Survivors" onTransferred={onTransferred} />);

    const transfer = screen.getByRole('button', { name: 'Transfer ownership' });
    fireEvent.change(screen.getByLabelText('New owner email'), { target: { value: 'new@example.com' } });
    fireEvent.change(screen.getByLabelText('Type Sunday Survivors to confirm'), { target: { value: 'Sunday survivor' } });
    expect(transfer).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Type Sunday Survivors to confirm'), { target: { value: 'Sunday Survivors' } });
    fireEvent.click(transfer);

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/admin/pools/pool-1/owner'),
      expect.objectContaining({ method: 'PUT', body: JSON.stringify({ email: 'new@example.com' }) }),
    ));
    expect(await screen.findByText('Ownership transferred to new@example.com. You remain a pool admin.')).toBeInTheDocument();
    expect(onTransferred).toHaveBeenCalledWith({ owner_email: 'new@example.com' });
  });

  test('shows ownership validation errors from the backend', async () => {
    fetch.mockResolvedValue({ ok: false, json: async () => ({ detail: 'New owner must join the pool before ownership can be transferred' }) });
    render(<OwnershipTransferControl poolId="pool-1" poolName="Sunday Survivors" />);

    fireEvent.change(screen.getByLabelText('New owner email'), { target: { value: 'outsider@example.com' } });
    fireEvent.change(screen.getByLabelText('Type Sunday Survivors to confirm'), { target: { value: 'Sunday Survivors' } });
    fireEvent.click(screen.getByRole('button', { name: 'Transfer ownership' }));

    expect(await screen.findByText('New owner must join the pool before ownership can be transferred')).toBeInTheDocument();
  });
});
