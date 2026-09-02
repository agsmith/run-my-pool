import { useEffect, useState } from 'react';
import { buildPoolJoinUrl } from '../utils/poolJoinUrl';

export default function LeaguePasswordViewer({ poolId, isPrivate, passwordChanged = 0 }) {
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [copyMessage, setCopyMessage] = useState('');

  useEffect(() => {
    setPassword('');
    setVisible(false);
    setMessage('');
    setCopyMessage('');
  }, [poolId, isPrivate, passwordChanged]);

  if (!isPrivate) return null;

  const inviteUrl = buildPoolJoinUrl(
    poolId,
    typeof window === 'undefined' ? '' : window.location.origin,
  );

  const copyInviteLink = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopyMessage('Invite link copied. Send it with the pool password.');
    } catch {
      setCopyMessage('Unable to copy automatically. Select and copy the invite link.');
    }
  };

  const revealPassword = async () => {
    if (password) {
      setVisible((current) => !current);
      return;
    }
    setLoading(true);
    setMessage('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/pools/${poolId}/join-password`,
        { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' },
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Unable to display the password');
      if (!data.available) {
        setMessage('The existing password cannot be displayed. Set a new password to make it viewable.');
        return;
      }
      setPassword(data.password);
      setVisible(true);
    } catch (error) {
      setMessage(error.message || 'Unable to display the password');
    } finally {
      setLoading(false);
    }
  };

  return <div className="admin-access-panel__current-password">
    <label htmlFor="private-pool-invite-link">Private invite link</label>
    <div>
      <input id="private-pool-invite-link" type="url" value={inviteUrl} readOnly />
      <button type="button" onClick={copyInviteLink}>Copy invite link</button>
    </div>
    {copyMessage && <small role="status">{copyMessage}</small>}
    <label htmlFor="current-league-password">Current password</label>
    <div>
      <input
        id="current-league-password"
        type={visible ? 'text' : 'password'}
        value={password || 'password'}
        readOnly
        aria-describedby={message ? 'current-league-password-message' : undefined}
      />
      <button type="button" onClick={revealPassword} disabled={loading}>
        {loading ? 'Loading…' : visible ? 'Hide password' : 'Show password'}
      </button>
    </div>
    {message && <small id="current-league-password-message" role="status">{message}</small>}
  </div>;
}
