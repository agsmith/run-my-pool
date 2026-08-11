import { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/router';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    const restoreSession = async () => {
      const cachedUser = localStorage.getItem('user');
      if (!cachedUser) {
        localStorage.removeItem('access_token');
        if (!cancelled) setLoading(false);
        return;
      }
      try {
        // The real credential is an HttpOnly cookie. The non-sensitive marker
        // keeps legacy request helpers from persisting the bearer token.
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
        }
      } catch {
        if (!cancelled) {
          setToken(null);
          setUser(null);
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    restoreSession();
    return () => { cancelled = true; };
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Invalid credentials');
      
      await res.json();

      // Persist only a non-sensitive marker; the credential is HttpOnly.
      const accessToken = 'cookie';
      setToken(accessToken);
      localStorage.setItem('access_token', accessToken);
      
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
      router.push('/dashboard');
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
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
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
