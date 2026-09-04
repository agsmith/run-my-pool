import { createContext, PropsWithChildren, useContext, useEffect, useState } from 'react';
import { apiFetch, login as apiLogin, logout as apiLogout, restoreSession } from '@/api/client';
import type { User } from '@/api/types';

type AuthState = { status: 'loading' | 'authenticated' | 'anonymous'; user: User | null; signIn(email: string, password: string): Promise<void>; signOut(): Promise<void> };
const AuthContext = createContext<AuthState | null>(null);
export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthState['status']>('loading');
  const [user, setUser] = useState<User | null>(null);
  const loadUser = async () => { const current = await apiFetch<User>('/auth/me'); setUser(current); setStatus('authenticated'); };
  useEffect(() => { restoreSession().then((ok) => ok ? loadUser() : setStatus('anonymous')).catch(() => setStatus('anonymous')); }, []);
  const signIn = async (email: string, password: string) => { await apiLogin(email, password); await loadUser(); };
  const signOut = async () => { await apiLogout(); setUser(null); setStatus('anonymous'); };
  return <AuthContext.Provider value={{ status, user, signIn, signOut }}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('useAuth must be used inside AuthProvider'); return value; }
