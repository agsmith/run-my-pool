import { formatAuditTimestamp } from '../utils/auditTime';

describe('audit timestamp formatting', () => {
  test('uses Eastern daylight time and identifies the timezone', () => {
    expect(formatAuditTimestamp('2026-09-01T12:00:00Z')).toBe('Sep 1, 2026, 8:00:00 AM EDT');
  });

  test('uses Eastern standard time when daylight saving time is inactive', () => {
    expect(formatAuditTimestamp('2026-01-15T12:00:00Z')).toBe('Jan 15, 2026, 7:00:00 AM EST');
  });

  test('returns a safe label for missing or invalid timestamps', () => {
    expect(formatAuditTimestamp()).toBe('Unknown Time');
    expect(formatAuditTimestamp('not-a-date')).toBe('Unknown Time');
  });
});
