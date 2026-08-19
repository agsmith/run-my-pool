const AUDIT_TIME_ZONE = 'America/New_York';

const auditTimeFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: AUDIT_TIME_ZONE,
  timeZoneName: 'short',
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  second: '2-digit',
});

export function formatAuditTimestamp(value, fallback = 'Unknown Time') {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return auditTimeFormatter.format(date);
}

export { AUDIT_TIME_ZONE };
