import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { baseStyles, createHoverHandlers, hoverEffects, createFocusHandlers, mobileStyles, getResponsiveStyle } from '../styles/globalStyles';
import { ResponsiveInput, ResponsiveButton, ResponsiveCard } from '../components/ResponsiveComponents';
import PasswordVisibilityButton from '../components/PasswordVisibilityButton';

function validateEmail(email) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
}

function validatePassword(password) {
  // At least 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special
  return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/.test(password);
}

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isMobile, setIsMobile] = useState(false);
  const { login, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (router.query.message) {
      setSuccessMessage(router.query.message);
    }
  }, [router.query.message]);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!validateEmail(email)) {
      setError('Please enter a valid email address.');
      return;
    }
    if (!validatePassword(password)) {
      setError('Password must be at least 8 characters, include uppercase, lowercase, number, and special character.');
      return;
    }
    try {
      const next = typeof router.query.next === 'string' && router.query.next.startsWith('/') && !router.query.next.startsWith('//')
        ? router.query.next
        : null;
      if (next) await login(email, password, next);
      else await login(email, password);
      // Cookie/session handling is done in backend and AuthContext
    } catch (err) {
      setError(err.message || 'Login failed');
    }
  };

  const containerStyles = {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: isMobile ? '1rem' : '2rem',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  };

  const cardStyles = {
    width: '100%',
    maxWidth: isMobile ? '100%' : '400px',
    backgroundColor: 'white',
    borderRadius: isMobile ? '12px' : '16px',
    padding: isMobile ? '1.5rem' : '2rem',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
  };

  return (
    <main style={containerStyles}>
      <ResponsiveCard style={cardStyles}>
        {/* Logo/Brand area */}
        <div className="auth-brand">
          <h1>
            <span className="product-football-mark auth-brand__mark" aria-hidden="true"><i /><i /><i /></span>
            <span>RUN MY <b>POOL</b></span>
          </h1>
          <p>Sign in to your account</p>
        </div>

        {/* Success Message */}
        {successMessage && (
          <div style={{
            backgroundColor: '#dcfce7',
            border: '1px solid #22c55e',
            color: '#15803d',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: isMobile ? '0.9rem' : '1rem'
          }}>
            {successMessage}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div style={{
            backgroundColor: '#fee2e2',
            border: '1px solid #ef4444',
            color: '#b91c1c',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: isMobile ? '0.9rem' : '1rem'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ width: '100%' }}>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{
              display: 'block',
              marginBottom: '0.5rem',
              color: '#374151',
              fontSize: isMobile ? '0.9rem' : '1rem',
              fontWeight: '500'
            }}>
              Email
            </label>
            <ResponsiveInput 
              type="email" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              required 
              placeholder="Enter your email"
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{
              display: 'block',
              marginBottom: '0.5rem',
              color: '#374151',
              fontSize: isMobile ? '0.9rem' : '1rem',
              fontWeight: '500'
            }}>
              Password
            </label>
            <div className="password-visibility-field">
              <ResponsiveInput
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="Enter your password"
              />
              <PasswordVisibilityButton
                visible={showPassword}
                onToggle={() => setShowPassword((current) => !current)}
                fieldName="login password"
              />
            </div>
          </div>

          <ResponsiveButton 
            type="submit" 
            disabled={loading} 
            variant="primary"
            style={{ width: '100%', marginTop: '1rem' }}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </ResponsiveButton>
        </form>

        {/* Footer Links */}
        <div style={{ 
          marginTop: '2rem', 
          textAlign: 'center',
          paddingTop: '1.5rem',
          borderTop: '1px solid #e5e7eb'
        }}>
          <div style={{ 
            display: 'flex', 
            flexDirection: isMobile ? 'column' : 'row', 
            gap: isMobile ? '1rem' : '1.5rem',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Link 
              href="/create-account" 
              style={{ 
                color: '#667eea',
                textDecoration: 'none',
                fontSize: isMobile ? '1rem' : '0.875rem',
                fontWeight: '600',
                transition: 'color 0.2s ease',
                padding: isMobile ? '0.5rem' : '0',
                minHeight: isMobile ? '44px' : 'auto',
                display: 'flex',
                alignItems: 'center'
              }}
              onMouseEnter={(e) => e.target.style.color = '#5a67d8'}
              onMouseLeave={(e) => e.target.style.color = '#667eea'}
            >
              Create New Account
            </Link>
            <Link 
              href="/forgot-password" 
              style={{ 
                color: '#6b7280',
                textDecoration: 'none',
                fontSize: isMobile ? '1rem' : '0.875rem',
                transition: 'color 0.2s ease',
                padding: isMobile ? '0.5rem' : '0',
                minHeight: isMobile ? '44px' : 'auto',
                display: 'flex',
                alignItems: 'center'
              }}
              onMouseEnter={(e) => e.target.style.color = '#374151'}
              onMouseLeave={(e) => e.target.style.color = '#6b7280'}
            >
              Forgot your password?
            </Link>
          </div>
        </div>
      </ResponsiveCard>
    </main>
  );
}
