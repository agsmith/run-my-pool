import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../components/ProtectedRoute';
import { useAuth } from '../../context/AuthContext';

export default function LeagueDetail() {
  const [league, setLeague] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const router = useRouter();
  const { user } = useAuth();
  const { id } = router.query;

  useEffect(() => {
    if (router.query.message) {
      setSuccessMessage(router.query.message);
    }
  }, [router.query.message]);

  useEffect(() => {
    if (id) {
      fetchLeague();
    }
  }, [id]);

  const fetchLeague = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setLeague(data);
      } else {
        setError('Failed to load league details');
      }
    } catch (err) {
      setError('Failed to load league details');
    } finally {
      setLoading(false);
    }
  };

  const handleEditLeague = () => {
    router.push(`/admin/league/${id}`);
  };

  const handleDeleteLeague = async () => {
    if (!confirm('Are you sure you want to delete this league? This action cannot be undone.')) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        router.push('/dashboard?message=League deleted successfully');
      } else {
        const errorData = await res.json();
        setError(errorData.detail || 'Failed to delete league');
      }
    } catch (err) {
      setError('Failed to delete league');
    }
  };

  if (!router.isReady) {
    return <div>Loading...</div>;
  }

  return (
    <ProtectedRoute>
      <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
        {loading ? (
          <div>Loading league details...</div>
        ) : error ? (
          <div style={{ color: 'red' }}>{error}</div>
        ) : league ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
              <h1>{league.name}</h1>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button 
                  onClick={() => router.push(`/league/${id}/entries`)}
                  style={{ 
                    backgroundColor: '#28a745', 
                    color: 'white', 
                    padding: '10px 20px', 
                    border: 'none', 
                    borderRadius: '5px', 
                    cursor: 'pointer',
                    fontSize: '16px'
                  }}
                >
                  My Entries
                </button>
                {league.owner_id === user?.id && (
                  <>
                    <button 
                      onClick={handleEditLeague}
                      style={{ 
                        backgroundColor: '#ffc107', 
                        color: 'black', 
                        padding: '10px 20px', 
                        border: 'none', 
                        borderRadius: '5px', 
                        cursor: 'pointer',
                        fontSize: '16px'
                      }}
                    >
                      Edit League
                    </button>
                    <button 
                      onClick={handleDeleteLeague}
                      style={{ 
                        backgroundColor: '#dc3545', 
                        color: 'white', 
                        padding: '10px 20px', 
                        border: 'none', 
                        borderRadius: '5px', 
                        cursor: 'pointer',
                        fontSize: '16px'
                      }}
                    >
                      Delete League
                    </button>
                  </>
                )}
              </div>
            </div>

            {successMessage && (
              <div style={{ 
                color: 'green', 
                backgroundColor: '#d4edda', 
                padding: '10px', 
                borderRadius: '4px',
                marginBottom: '1rem'
              }}>
                {successMessage}
              </div>
            )}

            <div style={{ 
              backgroundColor: '#f8f9fa', 
              padding: '1.5rem', 
              borderRadius: '8px',
              marginBottom: '2rem'
            }}>
              <h2>League Information</h2>
              <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}>
                <div>
                  <strong>Description:</strong>
                  <p>{league.description || 'No description provided'}</p>
                </div>
                <div>
                  <strong>Type:</strong>
                  <p>{league.is_private ? 'Private League' : 'Public League'}</p>
                </div>
                <div>
                  <strong>Lock Time:</strong>
                  <p>{league.lock_time ? new Date(league.lock_time).toLocaleString() : 'Not set'}</p>
                </div>
                <div>
                  <strong>Owner:</strong>
                  <p>{league.owner_id === user?.id ? 'You' : 'Another user'}</p>
                </div>
              </div>
            </div>

            <div style={{ 
              backgroundColor: '#fff', 
              border: '1px solid #ddd',
              padding: '1.5rem', 
              borderRadius: '8px',
              marginBottom: '2rem'
            }}>
              <h2>League Members</h2>
              <p style={{ color: '#666' }}>Member management coming soon...</p>
            </div>

            <div style={{ 
              backgroundColor: '#fff', 
              border: '1px solid #ddd',
              padding: '1.5rem', 
              borderRadius: '8px'
            }}>
              <h2>League Entries</h2>
              <p style={{ color: '#666' }}>Entry management coming soon...</p>
            </div>

            <div style={{ marginTop: '2rem' }}>
              <button 
                onClick={() => router.push('/dashboard')}
                style={{ 
                  backgroundColor: '#6c757d', 
                  color: 'white', 
                  padding: '10px 20px', 
                  border: 'none', 
                  borderRadius: '5px', 
                  cursor: 'pointer',
                  fontSize: '16px'
                }}
              >
                Back to Dashboard
              </button>
            </div>
          </>
        ) : (
          <div>League not found</div>
        )}
      </main>
    </ProtectedRoute>
  );
}
