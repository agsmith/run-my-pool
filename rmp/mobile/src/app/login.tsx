import { Image } from 'expo-image';
import { Redirect, router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/auth/AuthContext';
import { colors } from '@/theme';

export default function LoginScreen() {
  const { status, signIn } = useAuth();
  const { returnTo } = useLocalSearchParams<{ returnTo?: string }>();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  if (status === 'authenticated') return <Redirect href="/(tabs)" />;
  const submit = async () => {
    setError(''); setSubmitting(true);
    try { await signIn(email, password); router.replace(returnTo?.startsWith('/join/') ? returnTo as never : '/(tabs)'); }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to sign in'); }
    finally { setSubmitting(false); }
  };
  return <SafeAreaView style={styles.safe}><KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.page}>
    <View style={styles.brand}><Image source={require('../../assets/images/rmp-wordmark.png')} style={styles.logo} contentFit="contain" /><Text style={styles.kicker}>YOUR POOLS. YOUR PICKS.</Text><Text style={styles.title}>Welcome back.</Text><Text style={styles.copy}>Sign in to manage entries, make picks, and follow every pool.</Text></View>
    <View style={styles.card}>
      <Text style={styles.label}>Email</Text><TextInput autoCapitalize="none" autoComplete="email" keyboardType="email-address" value={email} onChangeText={setEmail} style={styles.input} placeholder="you@example.com" placeholderTextColor={colors.muted} />
      <Text style={styles.label}>Password</Text><TextInput autoComplete="current-password" secureTextEntry value={password} onChangeText={setPassword} style={styles.input} placeholder="Your password" placeholderTextColor={colors.muted} />
      {!!error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
      <Pressable disabled={submitting || !email || !password} onPress={submit} style={({ pressed }) => [styles.button, (pressed || submitting) && styles.pressed]}>{submitting ? <ActivityIndicator color={colors.ink} /> : <Text style={styles.buttonText}>Sign in</Text>}</Pressable>
      <Pressable onPress={() => router.push({ pathname: '/web', params: { path: '/forgot-password' } })}><Text style={styles.link}>Forgot password?</Text></Pressable>
    </View>
  </KeyboardAvoidingView></SafeAreaView>;
}
const styles = StyleSheet.create({ safe:{flex:1,backgroundColor:colors.ink},page:{flex:1,justifyContent:'center',padding:24,gap:28},brand:{gap:8},logo:{width:260,height:72,alignSelf:'center',marginBottom:20},kicker:{color:colors.lime,fontSize:12,fontWeight:'800',letterSpacing:2},title:{color:colors.text,fontSize:38,fontWeight:'900'},copy:{color:colors.muted,fontSize:16,lineHeight:24},card:{backgroundColor:colors.panel,padding:20,borderRadius:22,gap:10,borderWidth:1,borderColor:colors.line},label:{color:colors.text,fontWeight:'700',marginTop:4},input:{backgroundColor:colors.ink,borderColor:colors.line,borderWidth:1,borderRadius:12,padding:14,color:colors.text,fontSize:16},button:{marginTop:10,backgroundColor:colors.lime,borderRadius:12,padding:15,alignItems:'center'},buttonText:{color:colors.ink,fontSize:16,fontWeight:'900'},pressed:{opacity:.7},error:{color:colors.danger,lineHeight:20},link:{color:colors.cyan,textAlign:'center',fontWeight:'700',paddingTop:5} });
