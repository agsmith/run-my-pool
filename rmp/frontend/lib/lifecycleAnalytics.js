const SESSION_KEY = 'rmp_lifecycle_session';

function createSessionId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}_${Math.random().toString(36).slice(2)}`;
}

function lifecycleSessionId() {
  if (typeof window === 'undefined') return null;
  try {
    const existing = window.sessionStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const created = createSessionId();
    window.sessionStorage.setItem(SESSION_KEY, created);
    return created;
  } catch (_storageError) {
    return createSessionId();
  }
}

export function trackLifecycleEvent(event, properties = {}) {
  if (typeof window === 'undefined') return;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const sessionId = lifecycleSessionId();
  if (!apiUrl || !sessionId) return;

  const body = JSON.stringify({ event, session_id: sessionId, ...properties });
  fetch(`${apiUrl}/analytics/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'omit',
    keepalive: true,
    body,
  }).catch(() => {
    // Analytics must never interrupt the customer journey.
  });
}
