import ProtectedRoute from '../components/ProtectedRoute';
import { useAuth } from '../context/AuthContext';

export default function Profile() {
  const { user, logout } = useAuth();

  return (
    <ProtectedRoute>
      <main>
        <h1>User Profile</h1>
        <p><b>Email:</b> {user?.email}</p>
        {/* Add more user info and settings here */}
        <button onClick={logout}>Logout</button>
      </main>
    </ProtectedRoute>
  );
}
