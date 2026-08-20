import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import SiteDisclaimer from '../components/SiteDisclaimer';

describe('SiteDisclaimer', () => {
  test('displays the entertainment-use disclaimer in a footer', () => {
    render(<SiteDisclaimer />);

    expect(screen.getByText('For entertainment purposes only').closest('footer')).toHaveClass('site-disclaimer');
    expect(screen.getByRole('link', { name: 'Follow Run My Pool on Instagram' })).toHaveAttribute(
      'href',
      'https://www.instagram.com/runmypool/',
    );
    expect(screen.getByRole('link', { name: 'Follow Run My Pool on Instagram' })).toHaveAttribute('target', '_blank');
    expect(screen.getByText('@runmypool')).toBeInTheDocument();
  });
});
