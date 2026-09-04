import * as SecureStore from 'expo-secure-store';
import type { MobileSession } from './types';

const ACCESS_KEY = 'rmp.access-token';
const REFRESH_KEY = 'rmp.refresh-token';
export const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'https://runmypool.net').replace(/\/$/, '');
let accessToken: string | null = null;
let refreshPromise: Promise<boolean> | null = null;

async function saveSession(session: MobileSession) {
  accessToken = session.access_token;
  await Promise.all([SecureStore.setItemAsync(ACCESS_KEY, session.access_token), SecureStore.setItemAsync(REFRESH_KEY, session.refresh_token)]);
}
export async function clearSession() {
  accessToken = null;
  await Promise.all([SecureStore.deleteItemAsync(ACCESS_KEY), SecureStore.deleteItemAsync(REFRESH_KEY)]);
}
export async function login(email: string, password: string) {
  const response = await fetch(`${API_URL}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-RMP-Client': 'native' }, body: JSON.stringify({ email: email.trim().toLowerCase(), password }) });
  if (!response.ok) throw await apiError(response, 'Unable to sign in');
  const session = (await response.json()) as MobileSession;
  if (!session.refresh_token) throw new Error('Mobile session was not issued');
  await saveSession(session);
}
async function refreshSession(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
    if (!refreshToken) return false;
    const response = await fetch(`${API_URL}/auth/mobile-refresh`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }) });
    if (!response.ok) { await clearSession(); return false; }
    await saveSession((await response.json()) as MobileSession);
    return true;
  })().finally(() => { refreshPromise = null; });
  return refreshPromise;
}
export async function restoreSession() { accessToken = await SecureStore.getItemAsync(ACCESS_KEY); return refreshSession(); }
export async function logout() {
  const refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
  if (refreshToken) await fetch(`${API_URL}/auth/mobile-logout`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }) }).catch(() => undefined);
  await clearSession();
}
export async function apiFetch<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  if (!accessToken) accessToken = await SecureStore.getItemAsync(ACCESS_KEY);
  const headers = new Headers(init.headers);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (response.status === 401 && retry && await refreshSession()) return apiFetch<T>(path, init, false);
  if (!response.ok) throw await apiError(response, 'Request failed');
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}
async function apiError(response: Response, fallback: string) {
  const body = await response.json().catch(() => ({}));
  const detail = body?.detail;
  return new Error(typeof detail === 'string' ? detail : detail?.message || fallback);
}
