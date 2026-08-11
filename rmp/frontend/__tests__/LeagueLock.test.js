import { getLeagueJoinDeadline, isLeagueJoinLocked, parseLeagueDateTime } from '../utils/leagueLock';

describe('league join deadline', () => {
  const now = new Date('2026-08-10T17:00:00Z');

  test('treats timezone-less API datetimes as UTC', () => {
    expect(parseLeagueDateTime('2026-08-10T16:00:00').toISOString()).toBe('2026-08-10T16:00:00.000Z');
  });

  test('locks at and after the dedicated join deadline', () => {
    expect(isLeagueJoinLocked({ join_lock_time: '2026-08-10T17:00:00' }, now)).toBe(true);
    expect(isLeagueJoinLocked({ join_lock_time: '2026-08-10T17:00:01' }, now)).toBe(false);
  });

  test('falls back to the legacy lock only when recurring pick locks are not configured', () => {
    expect(isLeagueJoinLocked({ lock_time: '2026-08-10T16:00:00' }, now)).toBe(true);
    expect(getLeagueJoinDeadline({ lock_day_of_week: 0, lock_time: '2026-08-10T16:00:00' })).toBeNull();
  });

  test('an invalid or absent deadline remains open', () => {
    expect(isLeagueJoinLocked({}, now)).toBe(false);
    expect(isLeagueJoinLocked({ join_lock_time: 'not-a-date' }, now)).toBe(false);
  });
});
