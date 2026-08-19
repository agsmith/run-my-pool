import { formatAuditTimestamp } from '../utils/auditTime';

describe('audit timestamp formatting', () => {
  test('keeps recorded timestamps in UTC and identifies the timezone', () => {
    expect(formatAuditTimestamp('2026-09-01T12:00:00Z')).toBe('Sep 1, 2026, 12:00:00 PM UTC');
    expect(formatAuditTimestamp('2026-01-15T12:00:00Z')).toBe('Jan 15, 2026, 12:00:00 PM UTC');
  });

  test('returns a safe label for missing or invalid timestamps', () => {
    expect(formatAuditTimestamp()).toBe('Unknown Time');
    expect(formatAuditTimestamp('not-a-date')).toBe('Unknown Time');
  });
});
