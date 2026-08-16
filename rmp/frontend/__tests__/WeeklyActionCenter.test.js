import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WeeklyActionCenter from '../components/WeeklyActionCenter';

describe('WeeklyActionCenter', () => {
  test('guides a member with unfinished selections back to picks', async () => {
    const onAction = jest.fn();
    const user = userEvent.setup();
    render(
      <WeeklyActionCenter
        summary={{ week: 4, entries_remaining: 3, total_entries: 4, week_selections: 1, week_selection_total: 3 }}
        onAction={onAction}
      />,
    );

    expect(screen.getByRole('heading', { name: 'Week 4 Action Center' })).toBeInTheDocument();
    expect(screen.getByText('3/4')).toBeInTheDocument();
    expect(screen.getByText('1/3')).toBeInTheDocument();
    expect(screen.getByText(/2 selections still needed/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Continue picks' }));
    expect(onAction).toHaveBeenCalledWith(false);
  });

  test('sends a member with no entries to first-entry creation', async () => {
    const onAction = jest.fn();
    const user = userEvent.setup();
    render(
      <WeeklyActionCenter
        summary={{ week: 1, entries_remaining: 0, total_entries: 0, week_selections: 0, week_selection_total: 0 }}
        onAction={onAction}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Create your first entry' }));
    expect(onAction).toHaveBeenCalledWith(true);
  });

  test('confirms a completed week and supports reviewing picks', () => {
    render(
      <WeeklyActionCenter
        summary={{ week: 8, entries_remaining: 2, total_entries: 3, week_selections: 2, week_selection_total: 2 }}
        onAction={jest.fn()}
      />,
    );

    expect(screen.getByText(/you’re set for week 8/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Review picks' })).toBeInTheDocument();
  });

  test('keeps entries reachable when weekly status cannot load', async () => {
    const onAction = jest.fn();
    const user = userEvent.setup();
    render(<WeeklyActionCenter error onAction={onAction} />);

    expect(screen.getByText('Weekly status unavailable')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Open my entries' }));
    expect(onAction).toHaveBeenCalledWith(false);
  });
});
