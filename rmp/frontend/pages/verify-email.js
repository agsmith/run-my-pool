import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import BrandLogo from '../components/BrandLogo';
import { baseStyles } from '../styles/globalStyles';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

function safeInternalNext(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/dashboard';
}

export default function VerifyEmailPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('waiting');
  const [message, setMessage] = useState('Check your inbox and click the verification link to activate your account.');
  const verificationStarted = useRef(false);
  const next = safeInternalNext(router.query?.next);

  useEffect(() => {
    if (typeof router.query?.email === 'string') setEmail(router.query.email);
  }, [router.query?.email]);

  useEffect(() => {
    const token = typeof router.query?.token === 'string' ? router.query.token : '';
    if (!token || verificationStarted.current) return;
    verificationStarted.current = true;
    setStatus('verifying');
    setMessage('Verifying your email…');
    fetch(`${API_BASE_URL}/auth/verify-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    }).then(async (response) => {
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'This verification link is invalid or expired.');
      setStatus('verified');
      setMessage(body.message || 'Email verified successfully. You can now sign in.');
    }).catch((error) => {
      setStatus('error');
      setMessage(error.message || 'This verification link is invalid or expired.');
    });
  }, [router.query?.token]);

  const resend = async (event) => {
    event.preventDefault();
    setStatus('sending');
    setMessage('Requesting a new verification email…');
    try {
      const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to request another email.');
      setStatus('sent');
      setMessage(body.message);
    } catch (error) {
      setStatus('error');
      setMessage(error.message || 'Unable to request another email.');
    }
  };

  const loginHref = `/login?message=${encodeURIComponent('Email verified successfully. Please sign in.')}&next=${encodeURIComponent(next)}`;
  return <main className="auth-page" style={baseStyles.authPageContainer}>
    <div className="auth-card" style={baseStyles.authCard}>
      <div className="auth-brand"><h1><BrandLogo className="auth-brand__logo" alt="Run My Pool" variant="compact" priority /></h1><p>Verify your email</p></div>
      <div className={`auth-notice ${status === 'error' ? 'auth-notice--error' : 'auth-notice--success'}`} role="status">{message}</div>
      {status === 'verified' ? <Link className="auth-submit auth-link-button" href={loginHref}>Continue to sign in</Link> : <form onSubmit={resend} className="verification-resend-form">
        <label>Email address<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label>
        <button className="auth-submit" type="submit" disabled={status === 'sending' || !email.trim()}>{status === 'sending' ? 'Sending…' : 'Resend verification email'}</button>
      </form>}
      <p className="auth-field-hint">Links expire after 24 hours. Check your spam folder or contact <a href="mailto:support@runmypool.net">support@runmypool.net</a>.</p>
    </div>
  </main>;
}
