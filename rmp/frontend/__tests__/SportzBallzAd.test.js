import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import SportzBallzAd, { SPORTZBALLZ_ADS, sportzBallzAdIndex } from '../components/SportzBallzAd';

jest.mock('next/router', () => ({
  useRouter: () => ({ pathname: '/dashboard', asPath: '/dashboard' }),
}));

describe('SportzBallzAd', () => {
  test('includes all four approved SportzBallz campaigns', () => {
    expect(SPORTZBALLZ_ADS.map((ad) => ad.campaign)).toEqual([
      'prognostication',
      'bragging-rights',
      'next-pick',
      'daily-sportz-page',
    ]);
    expect(SPORTZBALLZ_ADS.find((ad) => ad.campaign === 'daily-sportz-page')).toMatchObject({
      destination: 'https://thedailysportspage.com',
      src: '/ads/sportzballz/daily-sportz-page.jpg',
    });
  });

  test('selects a stable starting creative for each route', () => {
    expect(sportzBallzAdIndex('/dashboard')).toBe(sportzBallzAdIndex('/dashboard'));
    expect(sportzBallzAdIndex('/dashboard')).toBeGreaterThanOrEqual(0);
    expect(sportzBallzAdIndex('/dashboard')).toBeLessThan(SPORTZBALLZ_ADS.length);
  });

  test('renders a sponsored, safely isolated link with campaign tracking', () => {
    render(<SportzBallzAd />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', expect.stringMatching(/^https:\/\/thedailysportspage\.com\?/));
    expect(link).toHaveAttribute('href', expect.stringContaining('utm_source=runmypool.net'));
    expect(link).toHaveAttribute('href', expect.stringContaining('utm_content='));
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', expect.stringContaining('sponsored'));
    expect(screen.getByRole('img')).toHaveAttribute('src', expect.stringMatching(/^\/ads\/sportzballz\/.+\.jpg$/));
    expect(screen.getByRole('img')).toHaveAttribute('width', '1456');
    expect(screen.getByRole('img')).toHaveAttribute('height', '308');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
