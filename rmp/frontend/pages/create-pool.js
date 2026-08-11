import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../components/ProtectedRoute';

export default function CreatePool() {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_private: false,
    join_password: '',
    lock_time: ''
  });
  const [ruleValues, setRuleValues] = useState({
    'weekly-lock-day': '4', // Thursday
    'weekly-lock-time': '17:00:00',
    'auto-pick-enabled': 'false',
    'auto-pick-strategy': 'random',
    'game-mode': 'pick_winner',
    'message-board-enabled': 'true'
  });
  const [availableRules, setAvailableRules] = useState([]);
  const [error, setError] = useState('');
  const [nameSuggestions, setNameSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    fetchAvailableRules();
  }, []);

  const fetchAvailableRules = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/rules?pool_type=survivor', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const rules = await res.json();
        setAvailableRules(rules);
      }
    } catch (err) {
      console.error('Failed to fetch rules:', err);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    if (name === 'name') {
      setNameSuggestions([]);
    }
  };

  const handleRuleChange = (ruleId, value) => {
    setRuleValues(prev => ({
      ...prev,
      [ruleId]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setNameSuggestions([]);
    setLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      
      // Convert rule values to the expected format
      const rule_values = Object.entries(ruleValues).map(([rule_id, rule_value]) => ({
        rule_id,
        rule_value
      }));
      
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/pools/create', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ...formData,
          lock_time: formData.lock_time ? formData.lock_time : null,
          rule_values
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        if (errorData.detail?.code === 'league_name_taken') {
          setNameSuggestions(errorData.detail.suggestions || []);
          throw new Error(errorData.detail.message);
        }
        throw new Error(
          typeof errorData.detail === 'string' ? errorData.detail : 'Failed to create pool'
        );
      }

      const league = await res.json();
      router.push(`/dashboard?message=Pool created successfully!`);
    } catch (err) {
      setError(err.message || 'Failed to create pool');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    router.push('/dashboard');
  };

  return (
    <ProtectedRoute>
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <header style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          padding: '1.5rem 2rem', 
          background: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid #e2e8f0'
        }}>
          <div style={{ color: '#1e293b', fontSize: '1.5rem', fontWeight: '700' }}>
            🏈 Run My Pool
          </div>
          <button
            type="button"
            onClick={handleCancel}
            style={{ 
              fontWeight: '500', 
              color: '#475569', 
              backgroundColor: '#f1f5f9', 
              border: '1px solid #cbd5e1', 
              borderRadius: '6px', 
              padding: '0.5rem 0.75rem', 
              transition: 'all 0.2s ease',
              cursor: 'pointer',
              fontSize: '1rem'
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = '#e2e8f0';
              e.target.style.borderColor = '#94a3b8';
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = '#f1f5f9';
              e.target.style.borderColor = '#cbd5e1';
            }}
          >
            Back to Dashboard
          </button>
        </header>

        {/* Main Content */}
        <main style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          padding: '2rem',
          background: 'transparent'
        }}>
          <h1 style={{ 
            fontSize: '3rem', 
            fontWeight: '800', 
            marginBottom: '1rem', 
            color: '#1e293b',
            textAlign: 'center'
          }}>
            Create New Pool
          </h1>
          
          <div style={{ 
            background: 'white', 
            borderRadius: '12px', 
            padding: '2rem',
            maxWidth: '800px',
            width: '100%',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
            border: '1px solid #e2e8f0'
          }}>
            <form onSubmit={handleSubmit}>
              {/* Basic Pool Information */}
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '0.875rem', 
                  fontWeight: '600', 
                  color: '#374151', 
                  marginBottom: '0.5rem' 
                }}>
                  Pool Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '1rem',
                    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                    outline: 'none'
                  }}
                  placeholder="Enter pool name"
                  onFocus={(e) => {
                    e.target.style.borderColor = '#4f46e5';
                    e.target.style.boxShadow = '0 0 0 3px rgba(79, 70, 229, 0.1)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#d1d5db';
                    e.target.style.boxShadow = 'none';
                  }}
                />
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '0.875rem', 
                  fontWeight: '600', 
                  color: '#374151', 
                  marginBottom: '0.5rem' 
                }}>
                  Description
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  rows={4}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '1rem',
                    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                    outline: 'none',
                    resize: 'vertical'
                  }}
                  placeholder="Optional description for your pool"
                  onFocus={(e) => {
                    e.target.style.borderColor = '#4f46e5';
                    e.target.style.boxShadow = '0 0 0 3px rgba(79, 70, 229, 0.1)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#d1d5db';
                    e.target.style.boxShadow = 'none';
                  }}
                />
              </div>

              {/* Pool Configuration Section */}
              <div style={{ 
                marginBottom: '2rem',
                padding: '1.5rem',
                backgroundColor: '#f8fafc',
                borderRadius: '12px',
                border: '1px solid #e2e8f0'
              }}>
                <h3 style={{ 
                  fontSize: '1.25rem', 
                  fontWeight: '700', 
                  color: '#1e293b',
                  marginBottom: '1.5rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <span style={{
                    display: 'inline-block',
                    width: '4px',
                    height: '20px',
                    backgroundColor: '#4f46e5',
                    borderRadius: '2px'
                  }}></span>
                  Pool Configuration
                </h3>

                {/* Timing Settings */}
                <div style={{ marginBottom: '2rem' }}>
                  <h4 style={{ 
                    fontSize: '1rem',
                    fontWeight: '600',
                    color: '#1e293b',
                    marginBottom: '1rem'
                  }}>
                    Lock Time Settings
                  </h4>
                  
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ 
                      display: 'block', 
                      fontSize: '0.875rem', 
                      fontWeight: '600', 
                      color: '#374151', 
                      marginBottom: '0.5rem' 
                    }}>
                      Weekly Lock Schedule
                    </label>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      <select
                        value={ruleValues['weekly-lock-day']}
                        onChange={(e) => handleRuleChange('weekly-lock-day', e.target.value)}
                        style={{
                          padding: '0.75rem',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '1rem',
                          transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                          outline: 'none',
                          minWidth: '140px', 
                          flex: 'none'
                        }}
                        onFocus={(e) => {
                          e.target.style.borderColor = '#4f46e5';
                          e.target.style.boxShadow = '0 0 0 3px rgba(79, 70, 229, 0.1)';
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#d1d5db';
                          e.target.style.boxShadow = 'none';
                        }}
                      >
                        <option value="0">Sunday</option>
                        <option value="1">Monday</option>
                        <option value="2">Tuesday</option>
                        <option value="3">Wednesday</option>
                        <option value="4">Thursday</option>
                        <option value="5">Friday</option>
                        <option value="6">Saturday</option>
                      </select>
                      <span style={{ color: '#64748b', fontWeight: '500' }}>at</span>
                      <input
                        type="time"
                        value={ruleValues['weekly-lock-time']?.substring(0, 5) || '17:00'}
                        onChange={(e) => handleRuleChange('weekly-lock-time', e.target.value + ':00')}
                        style={{
                          padding: '0.75rem',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '1rem',
                          transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                          outline: 'none',
                          width: '140px', 
                          flex: 'none'
                        }}
                        onFocus={(e) => {
                          e.target.style.borderColor = '#4f46e5';
                          e.target.style.boxShadow = '0 0 0 3px rgba(79, 70, 229, 0.1)';
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#d1d5db';
                          e.target.style.boxShadow = 'none';
                        }}
                      />
                    </div>
                    <small style={{ color: '#64748b', fontSize: '0.875rem', display: 'block', marginTop: '0.5rem' }}>
                      Picks will automatically lock each week on this day and time
                    </small>
                  </div>
                </div>

                {/* Game Rules */}
                <div style={{ marginBottom: '2rem' }}>
                  <h4 style={{ 
                    fontSize: '1rem',
                    fontWeight: '600',
                    color: '#1e293b',
                    marginBottom: '1rem'
                  }}>
                    Game Rules
                  </h4>

                  <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ 
                      display: 'block', 
                      fontSize: '0.875rem', 
                      fontWeight: '600', 
                      color: '#374151', 
                      marginBottom: '0.5rem' 
                    }}>
                      Pick Mode
                    </label>
                    <div style={{ 
                      display: 'flex', 
                      gap: '1.5rem',
                      padding: '1rem',
                      backgroundColor: 'white',
                      borderRadius: '8px',
                      border: '1px solid #e2e8f0'
                    }}>
                      <label style={{
                        display: 'flex',
                        alignItems: 'center',
                        fontSize: '0.875rem',
                        fontWeight: '500',
                        color: '#1e293b',
                        padding: '0.5rem 1rem',
                        borderRadius: '6px',
                        border: `2px solid ${ruleValues['game-mode'] === 'pick_winner' ? '#4f46e5' : '#e2e8f0'}`,
                        backgroundColor: ruleValues['game-mode'] === 'pick_winner' ? 'rgba(79, 70, 229, 0.1)' : 'transparent',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}>
                        <input
                          type="radio"
                          name="game-mode"
                          value="pick_winner"
                          checked={ruleValues['game-mode'] === 'pick_winner'}
                          onChange={(e) => handleRuleChange('game-mode', e.target.value)}
                          style={{ marginRight: '0.5rem' }}
                        />
                        <span style={{ fontWeight: '600' }}>Pick Winners</span>
                      </label>
                      <label style={{
                        display: 'flex',
                        alignItems: 'center',
                        fontSize: '0.875rem',
                        fontWeight: '500',
                        color: '#1e293b',
                        padding: '0.5rem 1rem',
                        borderRadius: '6px',
                        border: `2px solid ${ruleValues['game-mode'] === 'pick_loser' ? '#4f46e5' : '#e2e8f0'}`,
                        backgroundColor: ruleValues['game-mode'] === 'pick_loser' ? 'rgba(79, 70, 229, 0.1)' : 'transparent',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}>
                        <input
                          type="radio"
                          name="game-mode"
                          value="pick_loser"
                          checked={ruleValues['game-mode'] === 'pick_loser'}
                          onChange={(e) => handleRuleChange('game-mode', e.target.value)}
                          style={{ marginRight: '0.5rem' }}
                        />
                        <span style={{ fontWeight: '600' }}>Pick Losers</span>
                      </label>
                    </div>
                    <small style={{ color: '#64748b', fontSize: '0.875rem', display: 'block', marginTop: '0.5rem' }}>
                      Choose whether participants predict winning or losing teams each week
                    </small>
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'flex-start', 
                      gap: '0.75rem',
                      padding: '1rem',
                      backgroundColor: 'white',
                      borderRadius: '8px',
                      border: '1px solid #e2e8f0'
                    }}>
                      <input
                        type="checkbox"
                        checked={ruleValues['auto-pick-enabled'] === 'true'}
                        onChange={(e) => handleRuleChange('auto-pick-enabled', e.target.checked ? 'true' : 'false')}
                        style={{ marginTop: '0.125rem' }}
                      />
                      <div style={{ flex: 1 }}>
                        <label style={{ 
                          fontWeight: '600', 
                          color: '#1e293b', 
                          display: 'block', 
                          cursor: 'pointer',
                          marginBottom: '0.25rem'
                        }}>
                          Enable Auto-Pick
                        </label>
                        <small style={{ color: '#64748b', fontSize: '0.875rem', lineHeight: '1.4' }}>
                          Automatically select teams for users who don't make picks by the deadline
                        </small>
                      </div>
                    </div>

                    {ruleValues['auto-pick-enabled'] === 'true' && (
                      <div style={{ 
                        marginTop: '1rem',
                        marginLeft: '1rem',
                        padding: '1rem',
                        backgroundColor: 'rgba(248, 250, 252, 0.7)',
                        borderRadius: '8px',
                        borderLeft: '3px solid #4f46e5'
                      }}>
                        <label style={{ 
                          display: 'block', 
                          fontSize: '0.875rem', 
                          fontWeight: '600', 
                          color: '#374151', 
                          marginBottom: '0.5rem' 
                        }}>
                          Auto-Pick Strategy
                        </label>
                        <select
                          value={ruleValues['auto-pick-strategy']}
                          onChange={(e) => handleRuleChange('auto-pick-strategy', e.target.value)}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.5rem',
                            fontSize: '0.875rem',
                            color: '#1e293b',
                            backgroundColor: 'white',
                            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
                            outline: 'none',
                            transition: 'border-color 0.2s, box-shadow 0.2s'
                          }}
                          onFocus={(e) => {
                            e.target.style.borderColor = '#4f46e5';
                            e.target.style.boxShadow = '0 0 0 3px rgba(79, 70, 229, 0.1)';
                          }}
                          onBlur={(e) => {
                            e.target.style.borderColor = '#d1d5db';
                            e.target.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.05)';
                          }}
                        >
                          <option value="random">Random Team</option>
                          <option value="favorite">Favored Team</option>
                          <option value="underdog">Underdog Team</option>
                        </select>
                        <small style={{ color: '#64748b', fontSize: '0.875rem', display: 'block', marginTop: '0.5rem' }}>
                          How should teams be automatically selected for users who miss the deadline?
                        </small>
                      </div>
                    )}
                  </div>
                </div>

                {/* Pool Features */}
                <div>
                  <h4 style={{ 
                    fontSize: '1rem',
                    fontWeight: '600',
                    color: '#1e293b',
                    marginBottom: '1rem'
                  }}>
                    Pool Features
                  </h4>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'flex-start', 
                      gap: '0.75rem',
                      padding: '1rem',
                      backgroundColor: 'white',
                      borderRadius: '8px',
                      border: '1px solid #e2e8f0'
                    }}>
                      <input
                        type="checkbox"
                        checked={ruleValues['message-board-enabled'] === 'true'}
                        onChange={(e) => handleRuleChange('message-board-enabled', e.target.checked ? 'true' : 'false')}
                        style={{
                          width: '1rem',
                          height: '1rem',
                          borderRadius: '0.25rem',
                          border: '1px solid #d1d5db',
                          accentColor: '#4f46e5',
                          cursor: 'pointer',
                          marginTop: '0.125rem'
                        }}
                      />
                      <div style={{ flex: 1 }}>
                        <label style={{ 
                          fontWeight: '600', 
                          color: '#1e293b', 
                          display: 'block', 
                          cursor: 'pointer',
                          marginBottom: '0.25rem'
                        }}>
                          Enable Message Board
                        </label>
                        <small style={{ color: '#64748b', fontSize: '0.875rem', lineHeight: '1.4' }}>
                          Allow participants to post messages and discuss the pool
                        </small>
                      </div>
                    </div>

                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'flex-start', 
                      gap: '0.75rem',
                      padding: '1rem',
                      backgroundColor: 'white',
                      borderRadius: '8px',
                      border: '1px solid #e2e8f0'
                    }}>
                      <input
                        type="checkbox"
                        name="is_private"
                        checked={formData.is_private}
                        onChange={handleChange}
                        style={{
                          width: '1rem',
                          height: '1rem',
                          borderRadius: '0.25rem',
                          border: '1px solid #d1d5db',
                          accentColor: '#4f46e5',
                          cursor: 'pointer',
                          marginTop: '0.125rem'
                        }}
                      />
                      <div style={{ flex: 1 }}>
                        <label style={{ 
                          fontWeight: '600', 
                          color: '#1e293b', 
                          display: 'block', 
                          cursor: 'pointer',
                          marginBottom: '0.25rem'
                        }}>
                          Private Pool
                        </label>
                        <small style={{ color: '#64748b', fontSize: '0.875rem', lineHeight: '1.4' }}>
                          Private pools require a join password. Public pools are open to all users.
                        </small>
                      </div>
                    </div>
                    {formData.is_private && (
                      <div style={{ padding: '1rem', backgroundColor: 'white', border: '1px solid #e2e8f0' }}>
                        <label htmlFor="join_password" style={{ fontWeight: '600', color: '#1e293b', display: 'block', marginBottom: '0.5rem' }}>
                          Join Password
                        </label>
                        <input
                          id="join_password"
                          type="password"
                          name="join_password"
                          value={formData.join_password}
                          onChange={handleChange}
                          minLength={6}
                          maxLength={72}
                          required
                          autoComplete="new-password"
                          placeholder="At least 6 characters"
                          style={{ width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', fontSize: '1rem' }}
                        />
                        <small style={{ color: '#64748b', display: 'block', marginTop: '0.5rem' }}>
                          Players must enter this password before they can join the pool.
                        </small>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {error && (
                <div style={{
                  backgroundColor: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: '0.5rem',
                  padding: '1rem',
                  color: '#dc2626',
                  fontSize: '0.875rem'
                }}>
                  <div>{error}</div>
                  {nameSuggestions.length > 0 && (
                    <div style={{ marginTop: '0.75rem' }}>
                      <strong>Available names:</strong>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                        {nameSuggestions.map((suggestion) => (
                          <button
                            key={suggestion}
                            type="button"
                            onClick={() => {
                              setFormData(prev => ({ ...prev, name: suggestion }));
                              setError('');
                              setNameSuggestions([]);
                            }}
                            style={{
                              border: '1px solid #dc2626',
                              borderRadius: '999px',
                              padding: '0.35rem 0.75rem',
                              background: 'white',
                              color: '#991b1b',
                              cursor: 'pointer'
                            }}
                          >
                            Use {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    backgroundColor: loading ? '#94a3b8' : '#4f46e5',
                    color: 'white',
                    padding: '0.75rem 2rem',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: '600',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s ease',
                    opacity: loading ? 0.7 : 1
                  }}
                  onMouseEnter={(e) => {
                    if (!loading) {
                      e.target.style.backgroundColor = '#4338ca';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!loading) {
                      e.target.style.backgroundColor = '#4f46e5';
                    }
                  }}
                >
                  {loading ? 'Creating...' : 'Create Pool'}
                </button>
              </div>
            </form>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
