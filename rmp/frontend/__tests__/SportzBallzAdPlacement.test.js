import { shouldShowSportzBallzAd } from '../pages/_app';

describe('SportzBallz advertisement placement', () => {
  test.each([
    '/dashboard',
    '/leagues',
    '/pool/[id]',
    '/pool/[id]/entries',
    '/pool/[id]/matchups',
    '/pool/[id]/leaderboard',
    '/pool/[id]/members',
    '/pool/[id]/messages',
    '/league/[leagueId]/entries',
    '/message-board',
  ])('shows on member-facing route %s', (route) => {
    expect(shouldShowSportzBallzAd(route)).toBe(true);
  });

  test.each([
    '/',
    '/pricing',
    '/login',
    '/create-account',
    '/create-pool',
    '/billing/success',
    '/profile',
    '/support',
    '/admin',
    '/admin/league/[id]',
  ])('stays out of sensitive or task-focused route %s', (route) => {
    expect(shouldShowSportzBallzAd(route)).toBe(false);
  });
});
