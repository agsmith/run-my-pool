import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';

export const SPORTZBALLZ_ADS = [
  {
    campaign: 'prognostication',
    src: '/ads/sportzballz/prognostication.jpg',
    alt: "SportzBallz — Artificially Intelligent Athletic Competition Prognostication. See today's picks.",
  },
  {
    campaign: 'bragging-rights',
    src: '/ads/sportzballz/bragging-rights.jpg',
    alt: 'SportzBallz — AI picks. Human bragging rights. Get the picks.',
  },
  {
    campaign: 'next-pick',
    src: '/ads/sportzballz/next-pick.jpg',
    alt: 'SportzBallz — Stuck on your next pick? Let SportzBallz overthink it.',
  },
  {
    campaign: 'daily-sportz-page',
    src: '/ads/sportzballz/daily-sportz-page.jpg',
    alt: 'The Daily Sportz Page — daily MLB scores, stories, and stats from SportzBallz.',
  },
];

export function sportzBallzAdIndex(pathname = '') {
  return Array.from(pathname).reduce((total, character) => total + character.charCodeAt(0), 0) % SPORTZBALLZ_ADS.length;
}

export default function SportzBallzAd() {
  const router = useRouter();
  const routeKey = router.asPath?.split('?')[0] || router.pathname || '';
  const startingIndex = useMemo(() => sportzBallzAdIndex(routeKey), [routeKey]);
  const [activeIndex, setActiveIndex] = useState(startingIndex);

  useEffect(() => {
    setActiveIndex(startingIndex);
    const reducedMotion = typeof window !== 'undefined'
      && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) return undefined;

    const interval = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % SPORTZBALLZ_ADS.length);
    }, 9000);
    return () => window.clearInterval(interval);
  }, [startingIndex]);

  const activeAd = SPORTZBALLZ_ADS[activeIndex];
  const href = `https://sportzballz.io/?utm_source=runmypool.net&utm_medium=banner&utm_campaign=cross-promotion&utm_content=${activeAd.campaign}`;

  return (
    <aside className="sportzballz-ad" aria-label="Advertisement from SportzBallz">
      <span className="sportzballz-ad__label">Featured partner</span>
      <a
        className="sportzballz-ad__link"
        href={href}
        target="_blank"
        rel="sponsored noopener noreferrer"
        data-campaign={activeAd.campaign}
      >
        <img className="sportzballz-ad__image" src={activeAd.src} alt={activeAd.alt} width="1456" height="308" />
      </a>
    </aside>
  );
}
