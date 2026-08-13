import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { baseStyles, createHoverHandlers, hoverEffects, createFocusHandlers, mobileStyles, getResponsiveStyle } from '../styles/globalStyles';
import { ResponsiveInput, ResponsiveButton, ResponsiveCard } from '../components/ResponsiveComponents';
import PasswordVisibilityButton from '../components/PasswordVisibilityButton';
import BrandLogo from '../components/BrandLogo';

function validateEmail(email) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
}

const PLAN_LABELS = {
  free: 'Free',
  commissioner: 'Commish',
  pro: 'Pro',
  club: 'Club',
  'club-unlimited': 'Club Unlimited',
};

function safeInternalNext(next) {
  return typeof next === 'string' && next.startsWith('/') && !next.startsWith('//') ? next : '';
}

function planFromNext(next) {
  if (!safeInternalNext(next)) return '';
  if (next === '/create-pool?source=splash') return 'free';
  try {
    const plan = new URL(next, 'https://runmypool.net').searchParams.get('checkout');
    return PLAN_LABELS[plan] ? plan : '';
  } catch (_invalidNext) {
    return '';
  }
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
  const requestedNext = safeInternalNext(router.query.next);
  const continuationPlan = planFromNext(router.query.next);

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
    if (!password) {
      setError('Please enter your password.');
      return;
    }
    try {
      const next = requestedNext || null;
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
            <BrandLogo className="auth-brand__logo" alt="Run My Pool" priority />
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

        {continuationPlan && (
          <div className="auth-plan-selection" aria-label="Selected package">
            <div><span>Continue with</span><strong>{PLAN_LABELS[continuationPlan]}</strong></div>
            <Link href="/pricing">Change package</Link>
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
            <p className="auth-field-hint">Use your existing password. New passwords require 8+ characters with uppercase, lowercase, a number, and a special character.</p>
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
              href={continuationPlan
                ? `/create-account?plan=${continuationPlan}`
                : requestedNext
                  ? `/create-account?next=${encodeURIComponent(requestedNext)}`
                  : '/create-account'}
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
            <a href="mailto:support@runmypool.net" className="auth-support-link">Contact support</a>
          </div>
        </div>
      </ResponsiveCard>
    </main>
  );
}
