import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';

export default function SuperAdminRoute({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace('/login');
  }, [loading, router, user]);

  if (loading || !user) return <div>Loading...</div>;
  if (user.role !== 'SUPER_ADMIN') {
    return <main className="platform-admin-page"><div className="workspace-alert workspace-alert--error" role="alert">Platform admin access required.</div></main>;
  }
  return children;
}
