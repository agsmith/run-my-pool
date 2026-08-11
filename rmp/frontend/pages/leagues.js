import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../components/ProtectedRoute';
import PasswordVisibilityButton from '../components/PasswordVisibilityButton';

export default function Leagues() {
  const router = useRouter();
  const [pools, setPools] = useState([]);
  const [joinedIds, setJoinedIds] = useState(new Set());
  const [activeView, setActiveView] = useState('browse');
  const [search, setSearch] = useState('');
  const [visibility, setVisibility] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [membershipError, setMembershipError] = useState('');
  const [joiningId, setJoiningId] = useState(null);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [joinError, setJoinError] = useState('');
  const [joinErrorId, setJoinErrorId] = useState(null);
  const [submittingId, setSubmittingId] = useState(null);

  useEffect(() => {
    const loadPools = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const headers = { Authorization: `Bearer ${token}` };
        const [allResponse, mineResponse] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/`, { headers }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/my-pools`, { headers }),
        ]);
        if (!allResponse.ok) throw new Error('Unable to load pools');
        const allPools = await allResponse.json();
        setPools(allPools);
        if (mineResponse.ok) {
          const myPools = await mineResponse.json();
          setJoinedIds(new Set(myPools.map((pool) => pool.id)));
        } else {
          setMembershipError('Unable to load your pool memberships. Please try again.');
        }
      } catch (err) {
        setError(err.message || 'Unable to load pools');
      } finally {
        setLoading(false);
      }
    };
    loadPools();
  }, []);

  const filteredPools = useMemo(() => pools.filter((pool) => {
    const matchesText = `${pool.name} ${pool.description || ''}`.toLowerCase().includes(search.toLowerCase());
    const matchesVisibility = visibility === 'all'
      || (visibility === 'private' ? pool.is_private : !pool.is_private);
    const matchesMembership = activeView === 'browse' || joinedIds.has(pool.id);
    return matchesText && matchesVisibility && matchesMembership;
  }), [pools, search, visibility, activeView, joinedIds]);

  const joinPool = async (pool) => {
    if (pool.is_private && joiningId !== pool.id) {
      setJoiningId(pool.id);
      setPassword('');
      setShowPassword(false);
      setJoinError('');
      setJoinErrorId(null);
      return;
    }

    setSubmittingId(pool.id);
    setJoinError('');
    setJoinErrorId(null);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${pool.id}/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ password: pool.is_private ? password : null }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to join pool');
      setJoinedIds((current) => new Set([...current, pool.id]));
      setJoiningId(null);
      setPassword('');
      setShowPassword(false);
    } catch (err) {
      setJoinError(err.message || 'Unable to join pool');
      setJoinErrorId(pool.id);
    } finally {
      setSubmittingId(null);
    }
  };

  return (
    <ProtectedRoute>
      <main className="league-directory">
        <header className="league-directory__header">
          <span>Pool directory</span>
          <h1>Join a Pool</h1>
          <p>Public pools are open to every player. Private pools require the password supplied by the commissioner.</p>
        </header>

        <nav className="league-directory__views" aria-label="League directory views">
          <button
            type="button"
            className={activeView === 'browse' ? 'is-active' : ''}
            aria-current={activeView === 'browse' ? 'page' : undefined}
            onClick={() => setActiveView('browse')}
          >
            Browse Pools
          </button>
          <button
            type="button"
            className={activeView === 'mine' ? 'is-active' : ''}
            aria-current={activeView === 'mine' ? 'page' : undefined}
            onClick={() => setActiveView('mine')}
          >
            My Pools <span>{joinedIds.size}</span>
          </button>
        </nav>

        <section className="league-directory__controls" aria-label="Pool filters">
          <input
            type="search"
            placeholder="Search pools"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search pools"
          />
          <div>
            {['all', 'public', 'private'].map((option) => (
              <button
                type="button"
                key={option}
                className={visibility === option ? 'is-active' : ''}
                onClick={() => setVisibility(option)}
              >
                {option}
              </button>
            ))}
          </div>
          <button type="button" className="league-directory__create" onClick={() => router.push('/create-pool')}>
            Create pool
          </button>
        </section>

        {loading ? (
          <div className="league-directory__state">Loading pools…</div>
        ) : error ? (
          <div className="league-directory__state league-directory__state--error">{error}</div>
        ) : activeView === 'mine' && membershipError ? (
          <div className="league-directory__state league-directory__state--error">{membershipError}</div>
        ) : filteredPools.length === 0 ? (
          <div className="league-directory__state">
            {activeView === 'mine' ? 'You have not joined any pools that match these filters.' : 'No pools match this search.'}
          </div>
        ) : (
          <section className="league-directory__grid" aria-label="Available pools">
            {filteredPools.map((pool) => {
              const joined = joinedIds.has(pool.id);
              const enteringPassword = joiningId === pool.id;
              return (
                <article className="league-directory__card" key={pool.id}>
                  <div className="league-directory__card-head">
                    <span className={`league-directory__badge league-directory__badge--${pool.is_private ? 'private' : 'public'}`}>
                      {pool.is_private ? 'Private' : 'Public'}
                    </span>
                    {joined && <span className="league-directory__joined">Joined</span>}
                  </div>
                  <h2>{pool.name}</h2>
                  <p>{pool.description || 'A survivor pool ready for kickoff.'}</p>

                  {enteringPassword && !joined && (
                    <div className="league-directory__password">
                      <label htmlFor={`pool-password-${pool.id}`}>Pool password</label>
                      <div className="password-visibility-field">
                        <input
                          id={`pool-password-${pool.id}`}
                          type={showPassword ? 'text' : 'password'}
                          value={password}
                          maxLength={72}
                          onChange={(event) => setPassword(event.target.value)}
                          onKeyDown={(event) => event.key === 'Enter' && joinPool(pool)}
                          autoComplete="off"
                          autoFocus
                        />
                        <PasswordVisibilityButton
                          visible={showPassword}
                          onToggle={() => setShowPassword((current) => !current)}
                          fieldName="pool password"
                        />
                      </div>
                      {joinError && <span role="alert">{joinError}</span>}
                    </div>
                  )}

                  {joinErrorId === pool.id && !enteringPassword && (
                    <div className="league-directory__join-error" role="alert">{joinError}</div>
                  )}

                  <div className="league-directory__actions">
                    {joined ? (
                      <button type="button" className="league-directory__primary" onClick={() => router.push(`/pool/${pool.id}`)}>
                        Open pool
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="league-directory__primary"
                        disabled={submittingId === pool.id || (enteringPassword && password.length === 0)}
                        onClick={() => joinPool(pool)}
                      >
                        {submittingId === pool.id ? 'Joining…' : enteringPassword ? 'Unlock & join' : 'Join pool'}
                      </button>
                    )}
                    {enteringPassword && !joined && (
                      <button type="button" onClick={() => { setJoiningId(null); setJoinError(''); setJoinErrorId(null); setShowPassword(false); }}>
                        Cancel
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </section>
        )}
      </main>
    </ProtectedRoute>
  );
}
