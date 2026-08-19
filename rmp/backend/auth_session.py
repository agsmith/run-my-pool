from datetime import timedelta

# Persistent sessions are revocable server-side and renew after authenticated
# activity. Keep the access JWT short-lived; this session is the 180-day
# "remember me" credential stored only in an HttpOnly cookie.
PERSISTENT_SESSION_TTL = timedelta(days=180)
