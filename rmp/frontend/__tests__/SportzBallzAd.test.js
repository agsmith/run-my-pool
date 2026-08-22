import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import SportzBallzAd, { SPORTZBALLZ_ADS, sportzBallzAdIndex } from '../components/SportzBallzAd';

jest.mock('next/router', () => ({
  useRouter: () => ({ pathname: '/dashboard', asPath: '/dashboard' }),
}));

describe('SportzBallzAd', () => {
  test('includes the SportzBallz campaigns and all three Daily Sports Page banners', () => {
    expect(SPORTZBALLZ_ADS.map((ad) => ad.campaign)).toEqual([
      'prognostication',
      'bragging-rights',
      'next-pick',
      'daily-sports-page-classic',
      'daily-sports-page-night',
      'daily-sports-page-edition',
    ]);
    const dailySportsPageAds = SPORTZBALLZ_ADS.filter((ad) => ad.campaign.startsWith('daily-sports-page'));
    expect(dailySportsPageAds).toHaveLength(3);
    expect(dailySportsPageAds).toEqual(expect.arrayContaining([
      expect.objectContaining({
        destination: 'https://thedailysportspage.com/',
        src: '/ads/sportzballz/daily-sports-page-classic.png',
      }),
      expect.objectContaining({ src: '/ads/sportzballz/daily-sports-page-night.png' }),
      expect.objectContaining({ src: '/ads/sportzballz/daily-sports-page-edition.png' }),
    ]));
  });

  test('selects a stable starting creative for each route', () => {
    expect(sportzBallzAdIndex('/dashboard')).toBe(sportzBallzAdIndex('/dashboard'));
    expect(sportzBallzAdIndex('/dashboard')).toBeGreaterThanOrEqual(0);
    expect(sportzBallzAdIndex('/dashboard')).toBeLessThan(SPORTZBALLZ_ADS.length);
  });

  test('renders Daily Sports Page ads with reliable same-window tracked navigation', () => {
    render(<SportzBallzAd />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', expect.stringMatching(/^https:\/\/thedailysportspage\.com\/\?/));
    expect(link).toHaveAttribute('href', expect.stringContaining('utm_source=runmypool.net'));
    expect(link).toHaveAttribute('href', expect.stringContaining('utm_content='));
    expect(link).toHaveAttribute('target', '_self');
    expect(link).toHaveAttribute('rel', expect.stringContaining('sponsored'));
    expect(screen.getByRole('img')).toHaveAttribute('src', expect.stringMatching(/^\/ads\/sportzballz\/.+\.png$/));
    expect(screen.getByRole('img')).toHaveAttribute('width', '2115');
    expect(screen.getByRole('img')).toHaveAttribute('height', '744');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
