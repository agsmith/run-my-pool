import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '@/auth/AuthContext';

export default function RootLayout() {
  return (
    <SafeAreaProvider><AuthProvider><StatusBar style="light" /><Stack screenOptions={{ headerStyle: { backgroundColor: '#07181c' }, headerTintColor: '#f4f8f5', contentStyle: { backgroundColor: '#07181c' } }}>
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="login" options={{ headerShown: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="pool/[id]" options={{ title: 'Pool' }} />
    </Stack></AuthProvider></SafeAreaProvider>
  );
}
