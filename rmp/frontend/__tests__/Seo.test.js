import '@testing-library/jest-dom';
import { render } from '@testing-library/react';
import Seo from '../components/Seo';

jest.mock('next/head', () => ({
  __esModule: true,
  default: function MockHead({ children }) {
    return <>{children}</>;
  },
}));

describe('Seo', () => {
  test('renders canonical and social metadata for public pages', () => {
    render(<Seo title="Pricing" description="Pool pricing" path="/pricing" />);
    expect(document.title).toBe('Pricing | Run My Pool');
    expect(document.head.querySelector('link[rel="canonical"]')).toHaveAttribute('href', 'https://runmypool.net/pricing');
    expect(document.head.querySelector('meta[property="og:title"]')).toHaveAttribute('content', 'Pricing | Run My Pool');
    expect(document.head.querySelector('meta[name="twitter:card"]')).toHaveAttribute('content', 'summary');
  });

  test('marks private application pages noindex without a canonical', () => {
    render(<Seo title="Run My Pool" description="Private workspace" path="/dashboard" noIndex />);
    expect(document.head.querySelector('meta[name="robots"]')).toHaveAttribute('content', 'noindex, nofollow');
    expect(document.head.querySelector('link[rel="canonical"]')).not.toBeInTheDocument();
  });
});
