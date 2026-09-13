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

test('reports assignment count and lets commissioners refresh', () => {
  const onRefresh=jest.fn();
  render(<AdminAutoPickReport week={1} onWeekChange={()=>{}} records={[{audit_id:'a',user_email:'member@example.com',entry_name:'Entry One',team:'SEA',created_at:'2026-09-13T16:00:30'}]} loading={false} error="" onRefresh={onRefresh} />);
  expect(screen.getByRole('status')).toHaveTextContent('1 auto-picked entry for Week 1');
  fireEvent.click(screen.getByRole('button',{name:'Refresh auto-picks'}));
  expect(onRefresh).toHaveBeenCalledTimes(1);
});
