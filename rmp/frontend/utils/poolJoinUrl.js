export function buildPoolJoinUrl(poolId, origin = '') {
  if (!poolId || !origin) return '';
  return `${origin.replace(/\/$/, '')}/join/${encodeURIComponent(poolId)}`;
}
