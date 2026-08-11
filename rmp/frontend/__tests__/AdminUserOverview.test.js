import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import AdminUserOverview from '../components/AdminUserOverview';

const overview = {
  current_week: 4,
  total_users: 3,
  users: [
    { id: '1', email: 'owner@example.com', total_entries: 2, surviving_entries: 2, picked_entries: 2, has_current_week_pick: true, all_surviving_entries_picked: true, is_admin: true, admin_role: 'Owner' },
    { id: '2', email: 'partial@example.com', total_entries: 3, surviving_entries: 2, picked_entries: 1, has_current_week_pick: true, all_surviving_entries_picked: false, is_admin: false, admin_role: 'Member' },
    { id: '3', email: 'missing@example.com', total_entries: 1, surviving_entries: 1, picked_entries: 0, has_current_week_pick: false, all_surviving_entries_picked: false, is_admin: false, admin_role: 'Member' },
  ],
};

describe('AdminUserOverview', () => {
  test('shows roles, entry totals, and current-week completion without picks', () => {
    render(<AdminUserOverview overview={overview} loading={false} error="" onRefresh={() => {}} />);

    expect(screen.getByText(/Individual picks remain private/)).toHaveTextContent('Week 4 completion');
    expect(screen.getByText('owner@example.com')).toBeInTheDocument();
    expect(screen.getByText('Owner')).toBeInTheDocument();
    expect(screen.getByText('Complete')).toBeInTheDocument();
    expect(screen.getByText('Partial')).toBeInTheDocument();
    expect(screen.getByText('Missing')).toBeInTheDocument();
    expect(screen.getByText('2 / 2 picked')).toBeInTheDocument();
    expect(screen.queryByText(/buffalo|team picked/i)).not.toBeInTheDocument();
  });

  test('filters the directory by email and refreshes', () => {
    const onRefresh = jest.fn();
    render(<AdminUserOverview overview={overview} loading={false} error="" onRefresh={onRefresh} />);

    fireEvent.change(screen.getByLabelText('Search users'), { target: { value: 'partial' } });
    expect(screen.getByText('partial@example.com')).toBeInTheDocument();
    expect(screen.queryByText('owner@example.com')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});
