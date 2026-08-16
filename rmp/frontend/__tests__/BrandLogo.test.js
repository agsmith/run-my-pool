import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import BrandLogo from '../components/BrandLogo';

describe('BrandLogo', () => {
  test('uses the dark promotional wordmark by default', () => {
    render(<BrandLogo alt="Run My Pool" />);

    expect(screen.getByRole('img', { name: 'Run My Pool' })).toHaveAttribute(
      'src',
      '/brand/promotional/rmp-alt-horizontal-dark.png',
    );
  });

  test('supports the compact promotional wordmark', () => {
    render(<BrandLogo alt="Run My Pool" variant="compact" />);

    expect(screen.getByRole('img', { name: 'Run My Pool' })).toHaveAttribute(
      'src',
      '/brand/promotional/rmp-alt-compact-dark.png',
    );
  });

  test('uses the framed promotional symbol for icon-only placements', () => {
    render(<BrandLogo alt="Run My Pool" iconOnly />);

    expect(screen.getByRole('img', { name: 'Run My Pool' })).toHaveAttribute(
      'src',
      '/brand/promotional/rmp-alt-app-icon-framed.png',
    );
  });
});
