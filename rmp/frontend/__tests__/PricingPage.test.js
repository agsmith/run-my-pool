import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import PricingPage from '../pages/pricing';

const mockRouter = { query: {}, isReady: true };
jest.mock('next/router', () => ({ useRouter: () => mockRouter }));
jest.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: null, token: null }) }));

describe('PricingPage', () => {
  test('shows the recommended plans and prices', () => {
    render(<PricingPage />);
    expect(screen.getByRole('heading', { name: 'Free' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Commish' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Pro' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Club' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Club Unlimited' })).toBeInTheDocument();
    expect(screen.getByText('$39')).toBeInTheDocument();
    expect(screen.getByText('$79')).toBeInTheDocument();
    expect(screen.getByText('$129')).toBeInTheDocument();
    expect(screen.getByText('$249')).toBeInTheDocument();
  });

  test('makes the software-only payment model explicit', () => {
    render(<PricingPage />);
    expect(screen.getByText(/never takes a percentage/i)).toBeInTheDocument();
    expect(screen.getByText(/does not collect stakes or distribute winnings/i)).toBeInTheDocument();
  });

  test('links each plan to account creation', () => {
    render(<PricingPage />);
    expect(screen.getAllByRole('link', { name: /start free/i }).some((link) => link.getAttribute('href') === '/create-account?plan=free')).toBe(true);
    expect(screen.getByRole('link', { name: /choose commissioner/i })).toHaveAttribute('href', '/create-account?plan=commissioner');
    expect(screen.getByRole('link', { name: /choose pro/i })).toHaveAttribute('href', '/create-account?plan=pro');
    expect(screen.getByRole('link', { name: /choose club/i })).toHaveAttribute('href', '/create-account?plan=club');
    expect(screen.getByRole('link', { name: /go unlimited/i })).toHaveAttribute('href', '/create-account?plan=club-unlimited');
  });

  test('positions Club around multiple pools and historical access', () => {
    render(<PricingPage />);
    const clubCard = screen.getByRole('heading', { name: 'Club' }).closest('article');
    expect(clubCard).toHaveTextContent('Up to 5 active pools');
    expect(clubCard).toHaveTextContent('Full historical access');
    expect(clubCard).toHaveTextContent('$129');
    expect(clubCard).toHaveTextContent('per season');
    expect(clubCard).toHaveTextContent('$25 per additional 100 entries');
  });

  test('makes unlimited the clear choice for large pools', () => {
    render(<PricingPage />);
    const unlimitedCard = screen.getByRole('heading', { name: 'Club Unlimited' }).closest('article');
    expect(unlimitedCard).toHaveTextContent('$249');
    expect(unlimitedCard).toHaveTextContent('Unlimited entries');
    expect(unlimitedCard).toHaveTextContent('Unlimited active pools');
    expect(unlimitedCard).toHaveTextContent('No usage charges');
    expect(screen.getByText(/costs less once a Club account needs more than 900 entries/i)).toBeInTheDocument();
  });
});
