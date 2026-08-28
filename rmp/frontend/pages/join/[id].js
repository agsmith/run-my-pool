import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import BrandLogo from '../../components/BrandLogo';
import { useAuth } from '../../context/AuthContext';

export default function PoolInvitationPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const poolId = typeof router.query?.id === 'string' ? router.query.id : '';
  const [pool, setPool] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!router.isReady || !poolId) return;
    let cancelled = false;
    const loadInvitation = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/invite/${encodeURIComponent(poolId)}`, {
          cache: 'no-store',
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || 'This pool invitation is no longer available.');
        if (!cancelled) setPool(data);
      } catch (requestError) {
        if (!cancelled) setError(requestError.message || 'Unable to load this pool invitation.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadInvitation();
    return () => { cancelled = true; };
  }, [poolId, router.isReady]);

  const continuation = `/leagues?invite=${encodeURIComponent(poolId)}`;
  const joinPool = () => {
    if (authLoading) return;
    if (user) {
      router.push(continuation);
      return;
    }
    router.push(`/login?next=${encodeURIComponent(continuation)}`);
  };

  return (
    <main className="pool-invitation-page">
      <section className="pool-invitation-card" aria-live="polite">
        <BrandLogo className="pool-invitation-card__logo" alt="Run My Pool" variant="compact" priority />
        {loading ? (
          <p className="pool-invitation-card__state">Loading pool invitation…</p>
        ) : error ? (
          <>
            <h1>Invitation unavailable</h1>
            <p className="pool-invitation-card__error" role="alert">{error}</p>
            <Link href="/">Return to Run My Pool</Link>
          </>
        ) : (
          <>
            <span className="pool-invitation-card__eyebrow">You’re invited</span>
            <h1>{pool.name}</h1>
            <div className="pool-invitation-card__badges">
              <span>{pool.is_private ? 'Private pool' : 'Public pool'}</span>
            </div>
            <p>{pool.description || 'Join this pool on Run My Pool and make your picks.'}</p>
            {pool.is_private && <p className="pool-invitation-card__note">You’ll need the join code printed on your invitation after creating your account.</p>}
            <button type="button" onClick={joinPool} disabled={authLoading}>
              {authLoading ? 'Checking account…' : user ? 'Continue to join pool' : 'Log in to join pool'}
            </button>
            {!user && !authLoading && (
              <Link href={`/create-account?next=${encodeURIComponent(continuation)}`}>Need an account? Create one</Link>
            )}
          </>
        )}
      </section>
    </main>
  );
}
