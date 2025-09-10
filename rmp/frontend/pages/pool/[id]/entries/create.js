import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../../components/ProtectedRoute';

export default function CreateEntry() {
  const [league, setLeague] = useState(null);
  const [entryName, setEntryName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const router = useRouter();
  const { id } = router.query; // league id

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
      setPageLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!entryName.trim()) {
      setError('Entry name is required');
      setLoading(false);
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const entryData = {
        name: entryName.trim(),
        pool_id: id
      };
      console.log('Creating entry with data:', entryData);
      
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/entries/create', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(entryData)
      });

      if (!res.ok) {
        const errorData = await res.json();
        console.error('Entry creation error:', errorData);
        throw new Error(errorData.detail || `Failed to create entry: ${res.status} ${res.statusText}`);
      }

      const entry = await res.json();
      router.push(`/pool/${id}/entries?message=Entry "${entryName}" created successfully!`);
    } catch (err) {
      setError(err.message || 'Failed to create entry');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    router.push(`/pool/${id}/entries`);
  };

  if (!router.isReady || pageLoading) {
    return <div>Loading...</div>;
  }

  return (
    <ProtectedRoute>
      <main style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
        <h1>Create New Entry</h1>
        {league && (
          <h2 style={{ color: '#666', margin: '0.5rem 0 2rem 0' }}>for {league.name}</h2>
        )}
        
        <form onSubmit={handleSubmit} style={{ marginTop: '2rem' }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
              Entry Name *
            </label>
            <input
              type="text"
              value={entryName}
              onChange={(e) => setEntryName(e.target.value)}
              required
              style={{ 
                width: '100%', 
                padding: '10px', 
                border: '1px solid #ddd', 
                borderRadius: '4px',
                fontSize: '16px'
              }}
              placeholder="Enter a name for your entry"
            />
            <small style={{ color: '#666', marginTop: '0.25rem', display: 'block' }}>
              Choose a unique name for this entry (e.g., "My Main Entry", "Team Smith", etc.)
            </small>
          </div>

          {error && (
            <div style={{ 
              color: 'red', 
              backgroundColor: '#fee', 
              padding: '10px', 
              borderRadius: '4px',
              marginBottom: '1rem'
            }}>
              {error}
            </div>
          )}

          <div style={{ 
            backgroundColor: '#f8f9fa', 
            padding: '1rem', 
            borderRadius: '4px',
            marginBottom: '2rem'
          }}>
            <h3 style={{ margin: '0 0 0.5rem 0' }}>About Entries</h3>
            <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
              <li>Each entry represents your participation in this league</li>
              <li>You can create multiple entries if the league allows it</li>
              <li>Each entry will have its own set of picks for each week</li>
              <li>Entry names should be unique and meaningful to you</li>
            </ul>
          </div>

          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={handleCancel}
              style={{
                padding: '10px 20px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                backgroundColor: 'white',
                cursor: 'pointer',
                fontSize: '16px'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '10px 20px',
                border: 'none',
                borderRadius: '4px',
                backgroundColor: '#0070f3',
                color: 'white',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '16px',
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? 'Creating...' : 'Create Entry'}
            </button>
          </div>
        </form>
      </main>
    </ProtectedRoute>
  );
}
