import { useLocalSearchParams } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useEffect } from 'react';
import { StyleSheet, Text } from 'react-native';
import { Screen } from '@/components/Screen';
import { colors } from '@/theme';
export default function WebBridge(){const{path}=useLocalSearchParams<{path:string}>();useEffect(()=>{if(path)WebBrowser.openBrowserAsync(`https://runmypool.net${path.startsWith('/')?path:'/'}`);},[path]);return <Screen><Text style={styles.text}>Opening RunMyPool…</Text></Screen>}
const styles=StyleSheet.create({text:{color:colors.text,fontSize:18,fontWeight:'700'}});
