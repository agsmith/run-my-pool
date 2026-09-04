import { Redirect } from 'expo-router';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { useAuth } from '@/auth/AuthContext';
import { colors } from '@/theme';

export default function IndexScreen() {
  const { status } = useAuth();
  if (status === 'loading') return <View style={styles.loading}><ActivityIndicator color={colors.lime} size="large" /></View>;
  return <Redirect href={status === 'authenticated' ? '/(tabs)' : '/login'} />;
}

const styles = StyleSheet.create({ loading: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.ink } });
