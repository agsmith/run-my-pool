import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import SportzBallzAd, { SPORTZBALLZ_ADS, sportzBallzAdIndex } from '../components/SportzBallzAd';

jest.mock('next/router', () => ({
  useRouter: () => ({ pathname: '/dashboard', asPath: '/dashboard' }),
}));

describe('SportzBallzAd', () => {
  test('selects a stable starting creative for each route', () => {
    expect(sportzBallzAdIndex('/dashboard')).toBe(sportzBallzAdIndex('/dashboard'));
    expect(sportzBallzAdIndex('/dashboard')).toBeGreaterThanOrEqual(0);
    expect(sportzBallzAdIndex('/dashboard')).toBeLessThan(SPORTZBALLZ_ADS.length);
  });

  test('renders a sponsored, safely isolated link with campaign tracking', () => {
    render(<SportzBallzAd />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', expect.stringContaining('utm_source=runmypool.net'));
    expect(link).toHaveAttribute('href', expect.stringContaining('utm_content='));
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', expect.stringContaining('sponsored'));
    expect(screen.getByRole('img')).toHaveAttribute('src', expect.stringMatching(/^\/ads\/sportzballz\/.+\.jpg$/));
  });

  test('lets visitors select any of the three creatives', () => {
    render(<SportzBallzAd />);

    const thirdControl = screen.getByRole('button', { name: 'Show SportzBallz advertisement 3' });
    fireEvent.click(thirdControl);

    expect(thirdControl).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('img')).toHaveAttribute('src', SPORTZBALLZ_ADS[2].src);
    expect(screen.getByRole('link')).toHaveAttribute('data-campaign', SPORTZBALLZ_ADS[2].campaign);
  });
});
