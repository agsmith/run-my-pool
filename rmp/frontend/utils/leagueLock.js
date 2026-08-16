export function parseLeagueDateTime(value) {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;

  const raw = String(value).trim();
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
  const parsed = new Date(hasTimezone ? raw : `${raw}Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function getLeagueJoinDeadline(pool) {
  if (!pool) return null;
  if (pool.join_lock_time) return parseLeagueDateTime(pool.join_lock_time);

  const usesRecurringPickLock = pool.lock_day_of_week !== null && pool.lock_day_of_week !== undefined;
  return usesRecurringPickLock ? null : parseLeagueDateTime(pool.lock_time);
}

export function isLeagueJoinLocked(pool, now = new Date()) {
  const deadline = getLeagueJoinDeadline(pool);
  return deadline ? deadline.getTime() <= now.getTime() : false;
}
