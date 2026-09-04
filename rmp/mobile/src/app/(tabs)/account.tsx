import { router } from 'expo-router';
import { Pressable, StyleSheet, Text } from 'react-native';
import { useAuth } from '@/auth/AuthContext';
import { Screen } from '@/components/Screen';
import { colors } from '@/theme';
export default function AccountScreen(){const{user,signOut}=useAuth();const logout=async()=>{await signOut();router.replace('/login');};return <Screen><Text style={styles.title}>Account</Text><Text style={styles.label}>Signed in as</Text><Text style={styles.email}>{user?.email}</Text><Text style={styles.note}>Your session is securely remembered for up to 180 days and can be revoked by signing out.</Text><Pressable onPress={logout} style={styles.button}><Text style={styles.buttonText}>Sign out</Text></Pressable></Screen>}
const styles=StyleSheet.create({title:{color:colors.text,fontSize:32,fontWeight:'900'},label:{color:colors.muted,marginTop:12},email:{color:colors.text,fontSize:18,fontWeight:'800'},note:{color:colors.muted,lineHeight:22,backgroundColor:colors.panel,padding:16,borderRadius:14},button:{borderColor:colors.danger,borderWidth:1,borderRadius:12,padding:14,alignItems:'center',marginTop:20},buttonText:{color:colors.danger,fontWeight:'800'}});
