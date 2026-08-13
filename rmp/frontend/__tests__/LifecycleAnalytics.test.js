import { trackLifecycleEvent } from '../lib/lifecycleAnalytics';

describe('lifecycle analytics', () => {
  const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_URL = 'https://api.example.test';
    window.sessionStorage.clear();
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
  });

  afterAll(() => {
    process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
  });

  test('sends only the supplied allowlisted lifecycle payload with a session id', () => {
    trackLifecycleEvent('plan_selected', { page: 'pricing', plan: 'pro', source: 'pricing' });

    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.test/analytics/events',
      expect.objectContaining({ method: 'POST', credentials: 'omit', keepalive: true }),
    );
    const payload = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(payload).toEqual(expect.objectContaining({
      event: 'plan_selected',
      page: 'pricing',
      plan: 'pro',
      source: 'pricing',
    }));
    expect(payload.session_id).toMatch(/^[A-Za-z0-9_-]{16,64}$/);
    expect(payload).not.toHaveProperty('email');
  });

  test('never throws when analytics delivery fails', () => {
    global.fetch.mockRejectedValueOnce(new Error('network unavailable'));
    expect(() => trackLifecycleEvent('landing_view', { page: 'home', source: 'direct' })).not.toThrow();
  });
});
