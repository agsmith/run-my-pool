import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

function validatePassword(password) {
  // At least 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special
  return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/.test(password);
}

export default function ResetPassword() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState('');
  const router = useRouter();

  useEffect(() => {
    if (router.query.token) {
      setToken(router.query.token);
    } else if (router.isReady) {
      setError('Invalid or missing reset token. Please request a new password reset.');
    }
  }, [router.query.token, router.isReady]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    if (!validatePassword(password)) {
      setError('Password must be at least 8 characters, include uppercase, lowercase, number, and special character.');
      return;
    }
    
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (!token) {
      setError('Invalid reset token. Please request a new password reset.');
      return;
    }

    setLoading(true);
    
    try {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password })
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to reset password');
      }
      
      setSuccess('Password reset successful! Redirecting to login...');
      setTimeout(() => {
        router.push('/login?message=Password reset successful! Please log in with your new password.');
      }, 2000);
    } catch (err) {
      setError(err.message || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  if (!router.isReady) {
    return <div>Loading...</div>;
  }

  return (
    <main style={{ minHeight: '80vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
      <h1>Reset Password</h1>
      
      {token ? (
        <form onSubmit={handleSubmit} style={{ maxWidth: 400, width: '100%' }}>
          <label>New Password<br />
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required 
              style={{ width: '100%', padding: '8px', marginTop: '4px' }}
            />
          </label>
          <br />
          <label>Confirm New Password<br />
            <input 
              type="password" 
              value={confirmPassword} 
              onChange={e => setConfirmPassword(e.target.value)} 
              required 
              style={{ width: '100%', padding: '8px', marginTop: '4px' }}
            />
          </label>
          <br />
          <button 
            type="submit" 
            disabled={loading} 
            style={{ width: '100%', marginTop: '16px', padding: '12px' }}
          >
            {loading ? 'Resetting...' : 'Reset Password'}
          </button>
          
          {success && <div style={{ color: 'green', marginTop: 8, textAlign: 'center' }}>{success}</div>}
          {error && <div style={{ color: 'red', marginTop: 8, textAlign: 'center' }}>{error}</div>}
        </form>
      ) : (
        <div style={{ textAlign: 'center', maxWidth: '400px' }}>
          <p style={{ color: 'red' }}>{error}</p>
          <Link href="/forgot-password" style={{ color: '#0070f3', textDecoration: 'underline' }}>
            Request New Password Reset
          </Link>
        </div>
      )}
      
      <div style={{ marginTop: 24 }}>
        <Link href="/login" style={{ color: '#0070f3', textDecoration: 'underline' }}>
          Back to Login
        </Link>
      </div>
    </main>
  );
}
