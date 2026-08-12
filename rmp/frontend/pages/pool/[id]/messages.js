import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { useAuth } from '../../../context/AuthContext';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';

export default function MessageBoard() {
  const [pool, setPool] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [posting, setPosting] = useState(false);
  const router = useRouter();
  const { user } = useAuth();
  const { id: poolId } = router.query;

  useEffect(() => {
    if (poolId) {
      fetchPoolData();
      fetchMessages();
    }
  }, [poolId]);

  const fetchPoolData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools/${poolId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setPool(data);
      } else {
        setError('Failed to load pool details');
      }
    } catch (err) {
      setError('Failed to load pool details');
    }
  };

  const fetchMessages = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/messages/pool/${poolId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      } else if (res.status === 403) {
        setError('You must be a member of this pool to view messages');
      } else {
        setError('Failed to load messages');
      }
    } catch (err) {
      setError('Failed to load messages');
    } finally {
      setLoading(false);
    }
  };

  const handlePostMessage = async (e) => {
    e.preventDefault();
    
    if (!newMessage.trim()) {
      setError('Message cannot be empty');
      return;
    }

    if (newMessage.trim().length > 250) {
      setError('Message cannot exceed 250 characters');
      return;
    }

    setPosting(true);
    setError('');

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/messages/pool/${poolId}`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          pool_id: poolId,
          message: newMessage.trim()
        })
      });

      if (res.ok) {
        const newMsg = await res.json();
        setMessages(prev => [newMsg, ...prev]);
        setNewMessage('');
      } else {
        const errorData = await res.json();
        setError(errorData.detail || 'Failed to post message');
      }
    } catch (err) {
      setError('Failed to post message');
    } finally {
      setPosting(false);
    }
  };

  const handleDeleteMessage = async (messageId) => {
    if (!confirm('Are you sure you want to delete this message?')) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/messages/${messageId}`, {
        method: 'DELETE',
        headers: { 
          'Authorization': `Bearer ${token}`
        }
      });

      if (res.ok) {
        setMessages(prev => prev.filter(msg => msg.id !== messageId));
      } else {
        const errorData = await res.json();
        setError(errorData.detail || 'Failed to delete message');
      }
    } catch (err) {
      setError('Failed to delete message');
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return 'Unknown time';
    }
  };

  if (!router.isReady || loading) {
    return (
      <ProtectedRoute>
        <div style={{ 
          minHeight: '100vh', 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{ color: 'white', fontSize: '1.2rem' }}>Loading...</div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="product-page messages-page" style={{
        minHeight: '100vh', 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
        padding: '2rem 1rem'
      }}>
        <main className="product-main messages-main" style={{ maxWidth: '800px', margin: '0 auto' }}>
          <PoolWorkspaceNav poolId={poolId} poolName={pool?.name} active="messages" />
          <WorkspaceHeader
            eyebrow="Pool clubhouse"
            title="Pool messages"
            description="Updates, reminders, and week-to-week conversation for everyone in the pool."
            meta={`${messages.length} ${messages.length === 1 ? 'message' : 'messages'}`}
          />
          {/* Header */}
          <div className="legacy-page-title" style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: '12px',
            padding: '2rem',
            marginBottom: '2rem',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            <button
              onClick={() => router.back()}
              style={{
                background: 'rgba(255, 255, 255, 0.2)',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                borderRadius: '8px',
                color: 'white',
                padding: '0.5rem 1rem',
                cursor: 'pointer',
                fontSize: '0.9rem',
                marginBottom: '1rem',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.target.style.background = 'rgba(255, 255, 255, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.target.style.background = 'rgba(255, 255, 255, 0.2)';
              }}
            >
              ← Back
            </button>
            <h1 style={{ 
              color: 'white', 
              margin: '0 0 0.5rem 0', 
              fontSize: '2rem', 
              fontWeight: '700' 
            }}>
              💬 Message Board
            </h1>
            {pool && (
              <p style={{ 
                color: 'rgba(255, 255, 255, 0.9)', 
                margin: 0, 
                fontSize: '1.1rem' 
              }}>
                {pool.name}
              </p>
            )}
          </div>

          {/* Post Message Form */}
          <div className="product-panel message-composer" style={{
            background: 'white',
            borderRadius: '12px',
            padding: '2rem',
            marginBottom: '2rem',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)'
          }}>
            <h3 style={{ marginTop: 0, color: '#1a202c' }}>Post a Message</h3>
            <form onSubmit={handlePostMessage}>
              <textarea
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Share something with your league members... (max 250 characters)"
                maxLength={250}
                rows={4}
                style={{
                  width: '100%',
                  padding: '1rem',
                  border: '2px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '1rem',
                  resize: 'vertical',
                  minHeight: '100px',
                  fontFamily: 'inherit'
                }}
              />
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginTop: '1rem'
              }}>
                <span style={{ 
                  color: newMessage.length > 230 ? '#e53e3e' : '#6b7280',
                  fontSize: '0.9rem'
                }}>
                  {newMessage.length}/250 characters
                </span>
                <button
                  type="submit"
                  disabled={posting || !newMessage.trim()}
                  style={{
                    backgroundColor: posting || !newMessage.trim() ? '#cbd5e0' : '#667eea',
                    color: 'white',
                    padding: '0.75rem 1.5rem',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: '600',
                    cursor: posting || !newMessage.trim() ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                >
                  {posting ? 'Posting...' : 'Post Message'}
                </button>
              </div>
            </form>
          </div>

          {/* Error Display */}
          {error && (
            <div style={{
              backgroundColor: '#fed7d7',
              color: '#742a2a',
              padding: '1rem',
              borderRadius: '8px',
              marginBottom: '2rem',
              border: '1px solid #fc8181'
            }}>
              {error}
            </div>
          )}

          {/* Messages List */}
          <div className="product-panel message-feed" style={{
            background: 'white',
            borderRadius: '12px',
            padding: '2rem',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)'
          }}>
            <h3 style={{ marginTop: 0, color: '#1a202c', marginBottom: '1.5rem' }}>
              Messages ({messages.length})
            </h3>
            
            {messages.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '3rem',
                color: '#6b7280'
              }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>💬</div>
                <h4 style={{ color: '#4a5568', marginBottom: '0.5rem' }}>No messages yet</h4>
                <p>Be the first to post a message to your league members!</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {messages.map((message) => (
                  <article className="message-card"
                    key={message.id}
                    style={{
                      backgroundColor: message.user_id === user?.id ? '#f0f4ff' : '#f8f9fa',
                      border: `2px solid ${message.user_id === user?.id ? '#667eea' : '#e2e8f0'}`,
                      borderRadius: '12px',
                      padding: '1.5rem',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'flex-start',
                      marginBottom: '0.75rem'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{
                          backgroundColor: message.user_id === user?.id ? '#667eea' : '#6b7280',
                          color: 'white',
                          borderRadius: '50%',
                          width: '32px',
                          height: '32px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.875rem',
                          fontWeight: '600'
                        }}>
                          {message.user_email?.charAt(0).toUpperCase() || '?'}
                        </span>
                        <div>
                          <div className="message-card__author" style={{
                            fontWeight: '600', 
                            color: '#1a202c',
                            fontSize: '0.9rem'
                          }}>
                            {message.user_email || 'Unknown User'}
                            {message.user_id === user?.id && (
                              <span className="message-card__you" style={{
                                color: '#667eea', 
                                fontWeight: '500',
                                marginLeft: '0.5rem'
                              }}>
                                (You)
                              </span>
                            )}
                          </div>
                          <div className="message-card__timestamp" style={{
                            color: '#6b7280', 
                            fontSize: '0.75rem' 
                          }}>
                            {formatDate(message.created_at)}
                          </div>
                        </div>
                      </div>
                      {message.user_id === user?.id && (
                        <button
                          onClick={() => handleDeleteMessage(message.id)}
                          style={{
                            backgroundColor: 'transparent',
                            border: '1px solid #dc2626',
                            color: '#dc2626',
                            borderRadius: '6px',
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.75rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem'
                          }}
                          onMouseEnter={(e) => {
                            e.target.style.backgroundColor = '#dc2626';
                            e.target.style.color = 'white';
                          }}
                          onMouseLeave={(e) => {
                            e.target.style.backgroundColor = 'transparent';
                            e.target.style.color = '#dc2626';
                          }}
                          title="Delete your message"
                        >
                          🗑️ Delete
                        </button>
                      )}
                    </div>
                    <p style={{ 
                      margin: 0, 
                      color: '#2d3748', 
                      lineHeight: '1.6',
                      fontSize: '1rem'
                    }}>
                      {message.message}
                    </p>
                  </article>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
