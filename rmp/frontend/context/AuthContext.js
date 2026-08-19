import { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/router';

const AuthContext = createContext();
const SESSION_MARKER = 'session_expires_at';
const SESSION_TTL_MS = 180 * 24 * 60 * 60 * 1000;

const rememberSession = () => {
  localStorage.setItem(SESSION_MARKER, String(Date.now() + SESSION_TTL_MS));
};

const forgetSession = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  localStorage.removeItem(SESSION_MARKER);
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    const restoreSession = async () => {
      const cachedUser = localStorage.getItem('user');
      const markerExpiresAt = Number(localStorage.getItem(SESSION_MARKER));
      const hasUnexpiredMarker = Number.isFinite(markerExpiresAt) && markerExpiresAt > Date.now();
      // cachedUser supports sessions created before the marker was introduced.
      if (!cachedUser && !hasUnexpiredMarker) {
        forgetSession();
        if (!cancelled) setLoading(false);
        return;
      }
      try {
        // The real credential is an HttpOnly cookie. The non-sensitive marker
        // keeps legacy request helpers from persisting the bearer token. When
        // the marker indicates a remembered session, ask the backend to restore
        // the cookie even if cached user metadata is missing.
        localStorage.removeItem('access_token');
        const response = await fetch(process.env.NEXT_PUBLIC_API_URL + '/auth/me', {
          credentials: 'include',
        });
        if (!response.ok) throw new Error('No active session');
        const userData = await response.json();
        if (!cancelled) {
          setToken('cookie');
          setUser(userData);
          localStorage.setItem('access_token', 'cookie');
          localStorage.setItem('user', JSON.stringify(userData));
          rememberSession();
        }
      } catch {
        if (!cancelled) {
          setToken(null);
          setUser(null);
          forgetSession();
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    restoreSession();
    return () => { cancelled = true; };
  }, []);

  const login = async (email, password, redirectTo = '/dashboard') => {
    setLoading(true);
    try {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include',
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = body.detail;
        const loginError = new Error(
          (typeof detail === 'object' && detail?.message)
            || (typeof detail === 'string' && detail)
            || 'Invalid credentials',
        );
        loginError.code = typeof detail === 'object' ? detail?.code : undefined;
        throw loginError;
      }
      
      await res.json();

      // Persist only a non-sensitive marker; the credential is HttpOnly.
      const accessToken = 'cookie';
      setToken(accessToken);
      localStorage.setItem('access_token', accessToken);
      rememberSession();
      
      // Fetch full user info
      const userRes = await fetch(process.env.NEXT_PUBLIC_API_URL + '/auth/me', {
        credentials: 'include',
      });
      
      if (userRes.ok) {
        const userData = await userRes.json();
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
      } else {
        // Fallback to basic user info
        const basicUser = { email };
        setUser(basicUser);
        localStorage.setItem('user', JSON.stringify(basicUser));
      }
      
      setLoading(false);
      const safeRedirect = typeof redirectTo === 'string' && redirectTo.startsWith('/') && !redirectTo.startsWith('//')
        ? redirectTo
        : '/dashboard';
      router.push(safeRedirect);
    } catch (e) {
      setLoading(false);
      throw e;
    }
  };

  const logout = async () => {
    try {
      await fetch(process.env.NEXT_PUBLIC_API_URL + '/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } finally {
      setUser(null);
      setToken(null);
      forgetSession();
      router.push('/login');
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
