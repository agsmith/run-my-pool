import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import LeagueLockSettings, { toUtcIso } from '../components/LeagueLockSettings';

const league = {
  lock_day_of_week: 6,
  lock_time_of_day: '13:00:00',
  lock_timezone: 'America/New_York',
  join_lock_time: '2026-09-01T16:00:00',
};

describe('LeagueLockSettings', () => {
  test('shows the current weekly and registration lock times', () => {
    render(<LeagueLockSettings league={league} onSave={jest.fn()} />);

    expect(screen.getByText('Sunday at 1:00 PM')).toBeInTheDocument();
    expect(screen.getByText('Eastern Time (ET)')).toBeInTheDocument();
    expect(screen.getByText(/Sep 1, 2026, 12:00 PM EDT/)).toBeInTheDocument();
  });

  test('changes the weekly pick lock in a modal', async () => {
    const onSave = jest.fn().mockResolvedValue({});
    render(<LeagueLockSettings league={league} onSave={onSave} />);

    fireEvent.click(screen.getByRole('button', { name: 'Change weekly lock' }));
    expect(screen.getByRole('dialog', { name: 'Change weekly pick lock' })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Day of week'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('Time'), { target: { value: '12:00' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() => expect(onSave).toHaveBeenCalledWith({
      lock_day_of_week: 4,
      lock_time_of_day: '12:00',
      lock_timezone: 'America/New_York',
    }));
    expect(await screen.findByText('Weekly pick lock updated.')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  test('rehydrates and changes the registration deadline independently', async () => {
    const onSave = jest.fn().mockResolvedValue({});
    render(<LeagueLockSettings league={league} onSave={onSave} />);

    fireEvent.click(screen.getByRole('button', { name: 'Change registration lock' }));
    expect(screen.getByLabelText('Registration lock date')).toHaveValue('2026-09-01');
    expect(screen.getByLabelText('Registration lock time')).toHaveValue('12:00');
    fireEvent.change(screen.getByLabelText('Registration lock date'), { target: { value: '2026-09-08' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() => expect(onSave).toHaveBeenCalledWith({ join_lock_time: '2026-09-08 16:00:00' }));
    expect(await screen.findByText('League registration lock updated.')).toBeInTheDocument();
  });

  test('shows registration as open when no deadline is configured and closes dialogs with Escape', () => {
    render(<LeagueLockSettings league={{ ...league, join_lock_time: null }} onSave={jest.fn()} />);
    expect(screen.getByText('Not set')).toBeInTheDocument();
    expect(screen.getByText('Registration is currently open.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Change weekly lock' }));
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  test('converts local lock time using daylight saving time', () => {
    expect(toUtcIso('2026-09-01', '12:00', 'America/New_York')).toBe('2026-09-01 16:00:00');
    expect(toUtcIso('2026-12-01', '12:00', 'America/New_York')).toBe('2026-12-01 17:00:00');
  });
});
