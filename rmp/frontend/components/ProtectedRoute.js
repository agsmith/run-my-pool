import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      const requestedPath = typeof router.asPath === 'string' && router.asPath.startsWith('/') && !router.asPath.startsWith('//')
        ? router.asPath
        : '';
      router.replace(requestedPath && requestedPath !== '/' && requestedPath !== '/login'
        ? `/login?next=${encodeURIComponent(requestedPath)}`
        : '/login');
    }
  }, [user, loading, router]);

  if (loading || !user) return <div>Loading...</div>;
  return children;
}
