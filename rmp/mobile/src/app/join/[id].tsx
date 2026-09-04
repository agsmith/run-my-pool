import { Redirect, useLocalSearchParams } from 'expo-router';
import { useAuth } from '@/auth/AuthContext';

export default function JoinPoolLink() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status } = useAuth();
  if (status === 'loading') return null;
  if (status !== 'authenticated') {
    return <Redirect href={{ pathname: '/login', params: { returnTo: `/join/${id}` } }} />;
  }
  return <Redirect href={{ pathname: '/(tabs)/browse', params: { invite: id } }} />;
}
