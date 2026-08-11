import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../components/ProtectedRoute';
import { baseStyles, colors } from '../styles/globalStyles';

export default function CreateLeague() {
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
          typeof errorData.detail === 'string' ? errorData.detail : 'Failed to create league'
        );
      }

      const league = await res.json();
      router.push(`/dashboard?message=Pool created successfully!`);
    } catch (err) {
      setError(err.message || 'Failed to create league');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    router.push('/dashboard');
  };

  return (
    <ProtectedRoute>
      <div style={baseStyles.pageContainer}>
        {/* Header */}
        <header style={baseStyles.header}>
          <h1 style={baseStyles.pageTitle}>
            Create New Pool
          </h1>
          <button
            type="button"
            onClick={handleCancel}
            style={baseStyles.secondaryButton}
            onMouseEnter={(e) => baseStyles.handleButtonHover(e, 'secondary')}
            onMouseLeave={(e) => baseStyles.handleButtonLeave(e, 'secondary')}
          >
            Back to Dashboard
          </button>
        </header>

        {/* Main Content */}
        <main style={baseStyles.mainContent}>
          <div style={{...baseStyles.formContainer, maxWidth: '800px'}}>
            <form onSubmit={handleSubmit}>
              {/* Basic Pool Information */}
              <div style={baseStyles.formGroup}>
                <label style={baseStyles.label}>
                  Pool Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  style={baseStyles.input}
                  placeholder="Enter pool name"
                  onFocus={(e) => baseStyles.handleInputFocus(e)}
                  onBlur={(e) => baseStyles.handleInputBlur(e)}
                />
              </div>

              <div style={baseStyles.formGroup}>
                <label style={baseStyles.label}>
                  Description
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  rows={4}
                  style={{...baseStyles.input, resize: 'vertical'}}
                  placeholder="Optional description for your pool"
                  onFocus={(e) => baseStyles.handleInputFocus(e)}
                  onBlur={(e) => baseStyles.handleInputBlur(e)}
                />
              </div>

              {/* Pool Configuration Section */}
              <div style={{ 
                marginBottom: '2rem',
                padding: '1.5rem',
                backgroundColor: 'rgba(248, 250, 252, 0.5)',
                borderRadius: '12px',
                border: `1px solid ${colors.border}`
              }}>
                <h3 style={{ 
                  fontSize: '1.25rem', 
                  fontWeight: '700', 
                  color: colors.textPrimary,
                  marginBottom: '1.5rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <span style={{
                    display: 'inline-block',
                    width: '4px',
                    height: '20px',
                    backgroundColor: colors.primary,
                    borderRadius: '2px'
                  }}></span>
                  Pool Configuration
                </h3>

                {/* Timing Settings */}
                <div style={{ marginBottom: '2rem' }}>
                  <h4 style={{ 
                    fontSize: '1rem',
                    fontWeight: '600',
                    color: colors.textPrimary,
                    marginBottom: '1rem'
                  }}>
                    Lock Time Settings
                  </h4>
                  
                  <div style={{ ...baseStyles.formGroup, marginBottom: '1rem' }}>
                    <label style={baseStyles.label}>
                      Weekly Lock Schedule
                    </label>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      <select
                        value={ruleValues['weekly-lock-day']}
                        onChange={(e) => handleRuleChange('weekly-lock-day', e.target.value)}
                        style={{...baseStyles.input, minWidth: '140px', flex: 'none'}}
                        onFocus={(e) => baseStyles.handleInputFocus(e)}
                        onBlur={(e) => baseStyles.handleInputBlur(e)}
                      >
                        <option value="0">Sunday</option>
                        <option value="1">Monday</option>
                        <option value="2">Tuesday</option>
                        <option value="3">Wednesday</option>
                        <option value="4">Thursday</option>
                        <option value="5">Friday</option>
                        <option value="6">Saturday</option>
                      </select>
                      <span style={{ color: colors.textSecondary, fontWeight: '500' }}>at</span>
                      <input
                        type="time"
                        value={ruleValues['weekly-lock-time']?.substring(0, 5) || '17:00'}
                        onChange={(e) => handleRuleChange('weekly-lock-time', e.target.value + ':00')}
                        style={{...baseStyles.input, width: '140px', flex: 'none'}}
                        onFocus={(e) => baseStyles.handleInputFocus(e)}
                        onBlur={(e) => baseStyles.handleInputBlur(e)}
                      />
                    </div>
                    <small style={{ color: colors.textSecondary, fontSize: '0.875rem', display: 'block', marginTop: '0.5rem' }}>
                      Picks will automatically lock each week on this day and time
                    </small>
                  </div>
                </div>

                {/* Game Rules */}
                <div style={{ marginBottom: '2rem' }}>
                  <h4 style={{ 
                    fontSize: '1rem',
                    fontWeight: '600',
                    color: colors.textPrimary,
                    marginBottom: '1rem'
                  }}>
                    Game Rules
                  </h4>

                  <div style={{ ...baseStyles.formGroup, marginBottom: '1.5rem' }}>
                    <label style={baseStyles.label}>
                      Pick Mode
                    </label>
                    <div style={{ 
                      display: 'flex', 
                      gap: '1.5rem',
                      padding: '1rem',
                      backgroundColor: 'white',
                      borderRadius: '8px',
                      border: `1px solid ${colors.border}`
                    }}>
                      <label style={{
                        ...baseStyles.radioLabel,
                        padding: '0.5rem 1rem',
                        borderRadius: '6px',
                        border: `2px solid ${ruleValues['game-mode'] === 'pick_winner' ? colors.primary : colors.border}`,
                        backgroundColor: ruleValues['game-mode'] === 'pick_winner' ? `${colors.primary}10` : 'transparent',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}>
                        <input
                          type="radio"
                          name="game-mode"
                          value="pick_winner"
                          checked={ruleValues['game-mode'] === 'pick_winner'}
                          onChange={(e) => handleRuleChange('game-mode', e.target.value)}
                          style={{ ...baseStyles.radio, marginRight: '0.5rem' }}
                        />
                        <span style={{ fontWeight: '600' }}>Pick Winners</span>
                      </label>
                      <label style={{
                        ...baseStyles.radioLabel,
                        padding: '0.5rem 1rem',
                        borderRadius: '6px',
                        border: `2px solid ${ruleValues['game-mode'] === 'pick_loser' ? colors.primary : colors.border}`,
                        backgroundColor: ruleValues['game-mode'] === 'pick_loser' ? `${colors.primary}10` : 'transparent',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}>
                        <input
                          type="radio"
                          name="game-mode"
                          value="pick_loser"
                          checked={ruleValues['game-mode'] === 'pick_loser'}
                          onChange={(e) => handleRuleChange('game-mode', e.target.value)}
                          style={{ ...baseStyles.radio, marginRight: '0.5rem' }}
                        />
                        <span style={{ fontWeight: '600' }}>Pick Losers</span>
                      </label>
                    </div>
                    <small style={{ color: colors.textSecondary, fontSize: '0.875rem', display: 'block', marginTop: '0.5rem' }}>
                      Choose whether participants predict winning or losing teams each week
                    </small>
                  </div>

                  <div style={{ ...baseStyles.formGroup, marginBottom: '1rem' }}>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'flex-start', 
                      gap: '0.75rem',
                      padding: '1rem',
                      backgroundColor: 'white',
                      borderRadius: '8px',
                      border: `1px solid ${colors.border}`
                    }}>
                      <input
                        type="checkbox"
                        checked={ruleValues['auto-pick-enabled'] === 'true'}
                        onChange={(e) => handleRuleChange('auto-pick-enabled', e.target.checked ? 'true' : 'false')}
                        style={{...baseStyles.checkbox, marginTop: '0.125rem'}}
                      />
                      <div style={{ flex: 1 }}>
                        <label style={{ 
                          fontWeight: '600', 
                          color: colors.textPrimary, 
                          display: 'block', 
                          cursor: 'pointer',
                          marginBottom: '0.25rem'
                        }}>
                          Enable Auto-Pick
                        </label>
                        <small style={{ color: colors.textSecondary, fontSize: '0.875rem', lineHeight: '1.4' }}>
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
                        borderLeft: `3px solid ${colors.primary}`
                      }}>
                        <label style={{...baseStyles.label, marginBottom: '0.5rem'}}>
                          Auto-Pick Strategy
                        </label>
                        <select
                          value={ruleValues['auto-pick-strategy']}
                          onChange={(e) => handleRuleChange('auto-pick-strategy', e.target.value)}
                          style={baseStyles.input}
                          onFocus={(e) => baseStyles.handleInputFocus(e)}
                          onBlur={(e) => baseStyles.handleInputBlur(e)}
                        >
                          <option value="random">Random Team</option>
                          <option value="favorite">Favored Team</option>
                          <option value="underdog">Underdog Team</option>
                        </select>
                        <small style={{ color: colors.textSecondary, fontSize: '0.875rem', display: 'block', marginTop: '0.5rem' }}>
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
                    color: colors.textPrimary,
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
                      border: `1px solid ${colors.border}`
                    }}>
                      <input
                        type="checkbox"
                        checked={ruleValues['message-board-enabled'] === 'true'}
                        onChange={(e) => handleRuleChange('message-board-enabled', e.target.checked ? 'true' : 'false')}
                        style={{...baseStyles.checkbox, marginTop: '0.125rem'}}
                      />
                      <div style={{ flex: 1 }}>
                        <label style={{ 
                          fontWeight: '600', 
                          color: colors.textPrimary, 
                          display: 'block', 
                          cursor: 'pointer',
                          marginBottom: '0.25rem'
                        }}>
                          Enable Message Board
                        </label>
                        <small style={{ color: colors.textSecondary, fontSize: '0.875rem', lineHeight: '1.4' }}>
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
                      border: `1px solid ${colors.border}`
                    }}>
                      <input
                        type="checkbox"
                        name="is_private"
                        checked={formData.is_private}
                        onChange={handleChange}
                        style={{...baseStyles.checkbox, marginTop: '0.125rem'}}
                      />
                      <div style={{ flex: 1 }}>
                        <label style={{ 
                          fontWeight: '600', 
                          color: colors.textPrimary, 
                          display: 'block', 
                          cursor: 'pointer',
                          marginBottom: '0.25rem'
                        }}>
                          Private Pool
                        </label>
                        <small style={{ color: colors.textSecondary, fontSize: '0.875rem', lineHeight: '1.4' }}>
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
                <div style={baseStyles.errorAlert}>
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
                              border: '1px solid currentColor',
                              borderRadius: '999px',
                              padding: '0.35rem 0.75rem',
                              background: 'white',
                              color: 'inherit',
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
                    ...baseStyles.primaryButton,
                    opacity: loading ? 0.7 : 1,
                    cursor: loading ? 'not-allowed' : 'pointer'
                  }}
                  onMouseEnter={(e) => !loading && baseStyles.handleButtonHover(e, 'primary')}
                  onMouseLeave={(e) => !loading && baseStyles.handleButtonLeave(e, 'primary')}
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
