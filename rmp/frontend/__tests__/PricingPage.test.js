import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import PricingPage from '../pages/pricing';

describe('PricingPage', () => {
  test('shows the recommended four plans and prices', () => {
    render(<PricingPage />);
    expect(screen.getByRole('heading', { name: 'Free' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Commissioner' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Pro' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Club' })).toBeInTheDocument();
    expect(screen.getByText('$39')).toBeInTheDocument();
    expect(screen.getByText('$79')).toBeInTheDocument();
    expect(screen.getByText('$129')).toBeInTheDocument();
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
  });

  test('positions Club around multiple pools and historical access', () => {
    render(<PricingPage />);
    const clubCard = screen.getByRole('heading', { name: 'Club' }).closest('article');
    expect(clubCard).toHaveTextContent('Up to 5 active pools');
    expect(clubCard).toHaveTextContent('Full historical access');
    expect(clubCard).toHaveTextContent('$129');
    expect(clubCard).toHaveTextContent('per season');
  });
});
