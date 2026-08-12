import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import AdminAutoPickReport from '../components/AdminAutoPickReport';

test('shows weekly autopicks and changes the selected week', () => {
  const onWeekChange = jest.fn();
  render(<AdminAutoPickReport
    week={4}
    onWeekChange={onWeekChange}
    loading={false}
    error=""
    records={[{
      audit_id: 'audit-1', user_email: 'player@example.com', entry_name: 'Road Runner',
      team: 'BUF', created_at: '2026-09-30T17:00:00Z',
    }]}
  />);

  expect(screen.getByText('player@example.com')).toBeInTheDocument();
  expect(screen.getByText('Road Runner')).toBeInTheDocument();
  expect(screen.getByText('BUF')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Week'), { target: { value: '5' } });
  expect(onWeekChange).toHaveBeenCalledWith(5);
});

test('states when a week has no autopicks', () => {
  render(<AdminAutoPickReport week={2} onWeekChange={() => {}} loading={false} error="" records={[]} />);
  expect(screen.getByText('No autopicks were made for Week 2.')).toBeInTheDocument();
});
