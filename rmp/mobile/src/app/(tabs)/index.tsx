import { useCallback, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { apiFetch } from '@/api/client';
import type { Pool } from '@/api/types';
import { PoolCard } from '@/components/PoolCard';
import { Screen } from '@/components/Screen';
import { colors } from '@/theme';
export default function MyPoolsScreen(){const[pools,setPools]=useState<Pool[]>([]);const[loading,setLoading]=useState(true);const[error,setError]=useState('');const load=useCallback(async()=>{setError('');try{setPools(await apiFetch<Pool[]>('/pools/my-pools'));}catch(e){setError(e instanceof Error?e.message:'Unable to load pools');}finally{setLoading(false);}},[]);useFocusEffect(useCallback(()=>{load();},[load]));return <Screen><Text style={styles.kicker}>RUN MY POOL</Text><Text style={styles.title}>My Pools</Text><Text style={styles.copy}>Everything you need for this week, in one place.</Text>{loading?<ActivityIndicator color={colors.lime}/>:error?<Text style={styles.error}>{error}</Text>:pools.length?pools.map(p=><PoolCard key={p.id} pool={p}/>):<Text style={styles.empty}>You have not joined a pool yet. Open Browse to find one.</Text>}</Screen>}
const styles=StyleSheet.create({kicker:{color:colors.lime,fontSize:12,fontWeight:'900',letterSpacing:2},title:{color:colors.text,fontSize:34,fontWeight:'900'},copy:{color:colors.muted,fontSize:16,marginBottom:8},error:{color:colors.danger},empty:{color:colors.muted,backgroundColor:colors.panel,padding:20,borderRadius:16,lineHeight:22}});
