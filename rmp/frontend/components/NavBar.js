import Link from 'next/link';
import { useAuth } from '../context/AuthContext';

export default function NavBar() {
  const { user, logout } = useAuth();
  return (
    <nav style={{ padding: '1rem', background: '#222', color: '#fff' }}>
      <Link href="/" style={{ marginRight: 16, color: '#fff', textDecoration: 'none' }}>Home</Link>
      <Link href="/dashboard" style={{ marginRight: 16, color: '#fff', textDecoration: 'none' }}>Dashboard</Link>
      <Link href="/leagues" style={{ marginRight: 16, color: '#fff', textDecoration: 'none' }}>Leagues</Link>
      <Link href="/message-board" style={{ marginRight: 16, color: '#fff', textDecoration: 'none' }}>Message Board</Link>
      <Link href="/admin" style={{ marginRight: 16, color: '#fff', textDecoration: 'none' }}>Admin</Link>
      {user ? (
        <>
          <Link href="/profile" style={{ marginRight: 16, color: '#fff', textDecoration: 'none' }}>Profile</Link>
          <button onClick={logout} style={{ color: '#fff', background: 'none', border: 'none', cursor: 'pointer' }}>Logout</button>
        </>
      ) : (
        <>
          <Link href="/login" style={{ marginRight: 16, color: '#fff', textDecoration: 'none' }}>Login</Link>
          <Link href="/register" style={{ color: '#fff', textDecoration: 'none' }}>Register</Link>
        </>
      )}
    </nav>
  );
}
