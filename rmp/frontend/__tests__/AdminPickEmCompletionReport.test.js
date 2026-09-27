import '@testing-library/jest-dom';
import { fireEvent, render, screen, within } from '@testing-library/react';
import AdminPickEmCompletionReport from '../components/AdminPickEmCompletionReport';

const report = {
  week: 4,
  total_entries: 3,
  complete_entries: 1,
  entries_needing_attention: 2,
  required_picks: 16,
  requires_tiebreaker: true,
  incomplete_entries: [
    { entry_id: 'e1', entry_name: 'Bird Gang', participant_name: 'Alex', contact_email: 'alex@example.com', picks_made: 14, picks_required: 16, missing_picks: 2, tiebreaker_set: true, missing_tiebreaker: false },
    { entry_id: 'e2', entry_name: 'Paper Player', participant_name: 'Pat', contact_email: null, picks_made: 16, picks_required: 16, missing_picks: 0, tiebreaker_set: false, missing_tiebreaker: true },
  ],
};

describe('AdminPickEmCompletionReport', () => {
  test('shows missing picks and tiebreaker status by entry', () => {
    render(<AdminPickEmCompletionReport report={report} loading={false} error="" onWeekChange={() => {}} onRefresh={() => {}} />);

    expect(screen.getByText('2 of 3 entries need attention for Week 4.')).toBeInTheDocument();
    const alexRow = screen.getByText('Alex').closest('tr');
    expect(within(alexRow).getByText('14 / 16')).toBeInTheDocument();
    expect(within(alexRow).getByText('2 picks')).toBeInTheDocument();
    expect(within(alexRow).getByText('Set')).toBeInTheDocument();
    const paperRow = screen.getByText('Paper entry — follow up directly').closest('tr');
    expect(within(paperRow).getByText('Picks complete')).toBeInTheDocument();
    expect(within(paperRow).getByText('Missing')).toBeInTheDocument();
  });

  test('changes weeks and refreshes the selected week', () => {
    const onWeekChange = jest.fn();
    const onRefresh = jest.fn();
    render(<AdminPickEmCompletionReport report={report} loading={false} error="" onWeekChange={onWeekChange} onRefresh={onRefresh} />);

    fireEvent.change(screen.getByLabelText('Week'), { target: { value: '5' } });
    expect(onWeekChange).toHaveBeenCalledWith(5);
    fireEvent.click(screen.getByRole('button', { name: 'Refresh completion' }));
    expect(onRefresh).toHaveBeenCalledWith(5);
  });
});
