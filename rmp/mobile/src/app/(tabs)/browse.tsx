import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text } from 'react-native';
import { apiFetch } from '@/api/client';
import type { Pool } from '@/api/types';
import { PoolCard } from '@/components/PoolCard';
import { Screen } from '@/components/Screen';
import { colors } from '@/theme';
export default function BrowseScreen(){const[pools,setPools]=useState<Pool[]>([]);const[error,setError]=useState('');useEffect(()=>{apiFetch<Pool[]>('/pools/').then(setPools).catch(e=>setError(e.message));},[]);return <Screen><Text style={styles.title}>Pool Directory</Text><Text style={styles.copy}>Browse public and private pools. Private pools require their join code.</Text>{error?<Text style={styles.error}>{error}</Text>:pools.length?pools.map(p=><PoolCard key={p.id} pool={p}/>):<ActivityIndicator color={colors.lime}/>}</Screen>}
const styles=StyleSheet.create({title:{color:colors.text,fontSize:32,fontWeight:'900'},copy:{color:colors.muted,fontSize:16,lineHeight:23,marginBottom:6},error:{color:colors.danger}});
