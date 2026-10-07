import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import NflSurvivorPoolPage from '../pages/nfl-survivor-pool';
import NflPickEmPoolPage from '../pages/nfl-pick-em-pool';
import FootballSquaresPoolPage from '../pages/football-squares-pool';

const mockTrackLifecycleEvent = jest.fn();
jest.mock('../lib/lifecycleAnalytics', () => ({
  trackLifecycleEvent: (...args) => mockTrackLifecycleEvent(...args),
}));

beforeEach(() => mockTrackLifecycleEvent.mockClear());

test.each([
  [NflSurvivorPoolPage, /nfl survivor pool/i, 'survivor_landing'],
  [NflPickEmPoolPage, /nfl pick 'em pool/i, 'pickem_landing'],
  [FootballSquaresPoolPage, /football squares pool/i, 'squares_landing'],
])('renders an indexable pool-format page with a conversion path', (Page, heading, analyticsPage) => {
  render(<Page />);

  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(heading);
  expect(screen.getAllByRole('link', { name: /start free/i })[0]).toHaveAttribute('href', '/pricing');
  expect(screen.getByText(/does run my pool/i)).toBeInTheDocument();
  expect(mockTrackLifecycleEvent).toHaveBeenCalledWith('landing_view', {
    page: analyticsPage,
    source: 'direct',
  });
});
