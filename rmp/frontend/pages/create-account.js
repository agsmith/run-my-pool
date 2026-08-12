import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { baseStyles } from '../styles/globalStyles';
import PasswordVisibilityButton from '../components/PasswordVisibilityButton';

function validateEmail(email) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
}

function validatePassword(password) {
  // At least 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special
  return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/.test(password);
}

function registrationError(detail) {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg).filter(Boolean);
    if (messages.length) return messages.join(' ');
  }
  return 'Account creation failed. Please try again.';
}

export default function CreateAccount() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const selectedPlan = typeof router.query?.plan === 'string' ? router.query.plan : '';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!validateEmail(email)) {
      setError('Please enter a valid email address.');
      return;
    }
    if (!validatePassword(password)) {
      setError('Password must be at least 8 characters, include uppercase, lowercase, number, and special character.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(registrationError(data.detail));
      }
      const checkoutNext = selectedPlan && selectedPlan !== 'free'
        ? `/pricing?checkout=${encodeURIComponent(selectedPlan)}`
        : '/dashboard';
      router.push(`/login?message=${encodeURIComponent('Account created successfully! Please sign in with your new credentials.')}&next=${encodeURIComponent(checkoutNext)}`);
    } catch (err) {
      setError(err.message || 'Account creation failed. Please try again.');
    }
    setLoading(false);
  };

  return (
    <main className="auth-page" style={baseStyles.authPageContainer}>
      <div className="auth-card auth-card--create" style={baseStyles.authCard}>
        {/* Logo/Brand area */}
        <div className="auth-brand">
          <h1>
            <span className="product-football-mark auth-brand__mark" aria-hidden="true"><i /><i /><i /></span>
            <span>RUN MY <b>POOL</b></span>
          </h1>
          <p>Create your new account</p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="auth-notice auth-notice--error" style={{
            backgroundColor: '#fed7d7',
            color: '#742a2a',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            border: '1px solid #fc8181',
            fontSize: '0.875rem'
          }}>
            {error}
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="auth-notice auth-notice--success" style={{
            backgroundColor: '#f0fff4',
            color: '#22543d',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            border: '1px solid #9ae6b4',
            fontSize: '0.875rem'
          }}>
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ width: '100%' }}>
          <div className="auth-form-field" style={{ marginBottom: '1.5rem' }}>
            <label style={{ 
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '0.5rem'
            }}>
              Email Address
            </label>
            <input 
              type="email" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              required 
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                border: '2px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '1rem',
                transition: 'all 0.2s ease',
                outline: 'none',
                backgroundColor: '#fafafa'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#667eea';
                e.target.style.backgroundColor = 'white';
                e.target.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.1)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#e5e7eb';
                e.target.style.backgroundColor = '#fafafa';
                e.target.style.boxShadow = 'none';
              }}
              placeholder="Enter your email"
            />
          </div>

          <div className="auth-form-field" style={{ marginBottom: '1.5rem' }}>
            <label style={{ 
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '0.5rem'
            }}>
              Password
            </label>
            <div className="password-visibility-field">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="Enter your password"
              />
              <PasswordVisibilityButton visible={showPassword} onToggle={() => setShowPassword((current) => !current)} fieldName="new account password" />
            </div>
          </div>

          <div className="auth-form-field" style={{ marginBottom: '1.5rem' }}>
            <label style={{ 
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '0.5rem'
            }}>
              Confirm Password
            </label>
            <div className="password-visibility-field">
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                required
                placeholder="Confirm your password"
              />
              <PasswordVisibilityButton visible={showConfirmPassword} onToggle={() => setShowConfirmPassword((current) => !current)} fieldName="password confirmation" />
            </div>
          </div>

          <button className="auth-submit"
            type="submit" 
            disabled={loading} 
            style={{ 
              width: '100%',
              padding: '0.875rem 1rem',
              backgroundColor: loading ? '#9ca3af' : '#667eea',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease',
              transform: loading ? 'none' : 'translateY(0)',
              boxShadow: loading ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.4)'
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.target.style.backgroundColor = '#5a67d8';
                e.target.style.transform = 'translateY(-1px)';
                e.target.style.boxShadow = '0 6px 16px rgba(102, 126, 234, 0.5)';
              }
            }}
            onMouseLeave={(e) => {
              if (!loading) {
                e.target.style.backgroundColor = '#667eea';
                e.target.style.transform = 'translateY(0)';
                e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
              }
            }}
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        {/* Footer Links */}
        <div className="auth-footer" style={{
          marginTop: '2rem', 
          textAlign: 'center',
          paddingTop: '1.5rem',
          borderTop: '1px solid #e5e7eb'
        }}>
          <Link 
            href={selectedPlan && selectedPlan !== 'free' ? `/login?next=${encodeURIComponent(`/pricing?checkout=${selectedPlan}`)}` : '/login'}
            style={{ 
              color: '#6b7280',
              textDecoration: 'none',
              fontSize: '0.875rem',
              transition: 'color 0.2s ease'
            }}
            onMouseEnter={(e) => e.target.style.color = '#374151'}
            onMouseLeave={(e) => e.target.style.color = '#6b7280'}
          >
            Already have an account? Sign in
          </Link>
        </div>
      </div>
    </main>
  );
}
