const SESSION_KEY = 'rmp_lifecycle_session';
const ATTRIBUTION_KEY = 'rmp_first_touch_attribution';
const SEARCH_HOSTS = /(^|\.)(google|bing|yahoo|duckduckgo)\./i;

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

function cleanAttributionValue(value, maxLength = 100) {
  if (typeof value !== 'string') return '';
  return value.trim().replace(/[^A-Za-z0-9._~:/?&=+%-]/g, '').slice(0, maxLength);
}

function cleanCampaignValue(value) {
  if (typeof value !== 'string') return '';
  return value.trim().replace(/[^A-Za-z0-9._~:+%-]/g, '').slice(0, 100);
}

function firstTouchAttribution() {
  if (typeof window === 'undefined') return {};
  try {
    const existing = window.localStorage.getItem(ATTRIBUTION_KEY);
    if (existing) return JSON.parse(existing);

    const params = new URLSearchParams(window.location.search);
    let referrerHost = '';
    try {
      referrerHost = document.referrer ? new URL(document.referrer).hostname : '';
    } catch (_invalidReferrer) {
      referrerHost = '';
    }
    const utmSource = cleanCampaignValue(params.get('utm_source'));
    const utmMedium = cleanCampaignValue(params.get('utm_medium'));
    const utmCampaign = cleanCampaignValue(params.get('utm_campaign'));
    const utmContent = cleanCampaignValue(params.get('utm_content'));
    const acquisitionChannel = utmSource
      ? 'campaign'
      : SEARCH_HOSTS.test(referrerHost)
        ? 'organic_search'
        : referrerHost && referrerHost !== window.location.hostname
          ? 'referral'
          : 'direct';
    const attribution = {
      acquisition_channel: acquisitionChannel,
      landing_path: cleanAttributionValue(window.location.pathname, 160) || '/',
      ...(referrerHost ? { referrer_host: cleanAttributionValue(referrerHost, 160) } : {}),
      ...(utmSource ? { utm_source: utmSource } : {}),
      ...(utmMedium ? { utm_medium: utmMedium } : {}),
      ...(utmCampaign ? { utm_campaign: utmCampaign } : {}),
      ...(utmContent ? { utm_content: utmContent } : {}),
    };
    window.localStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(attribution));
    return attribution;
  } catch (_storageError) {
    return { acquisition_channel: 'direct', landing_path: window.location.pathname || '/' };
  }
}

export function trackLifecycleEvent(event, properties = {}) {
  if (typeof window === 'undefined') return;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const sessionId = lifecycleSessionId();
  if (!apiUrl || !sessionId) return;

  const body = JSON.stringify({ event, session_id: sessionId, ...firstTouchAttribution(), ...properties });
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
