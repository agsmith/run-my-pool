import { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/router';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Try to load user/token from localStorage on mount
    const t = localStorage.getItem('access_token');
    const u = localStorage.getItem('user');
    if (t && u) {
      setToken(t);
      setUser(JSON.parse(u));
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if (!res.ok) throw new Error('Invalid credentials');
      
      const data = await res.json();
      const accessToken = data.access_token;
      
      // Store token
      setToken(accessToken);
      localStorage.setItem('access_token', accessToken);
      
      // Fetch full user info
      const userRes = await fetch(process.env.NEXT_PUBLIC_API_URL + '/auth/me', {
        headers: { 'Authorization': `Bearer ${accessToken}` }
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

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    router.push('/login');
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
