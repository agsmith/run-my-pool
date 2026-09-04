import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { Pool } from '@/api/types';
import { colors } from '@/theme';
export function PoolCard({ pool }: { pool: Pool }) { return <Pressable onPress={() => router.push(`/pool/${pool.id}`)} style={({pressed})=>[styles.card,pressed&&{opacity:.7}]}><View style={styles.row}><Text style={styles.name}>{pool.name}</Text><Text style={styles.arrow}>›</Text></View><View style={styles.meta}><Text style={styles.badge}>{pool.pool_type?.toUpperCase()}</Text>{pool.role&&<Text style={styles.role}>{pool.role}</Text>}</View></Pressable>; }
const styles=StyleSheet.create({card:{backgroundColor:colors.panel,padding:18,borderRadius:18,borderWidth:1,borderColor:colors.line,gap:14},row:{flexDirection:'row',alignItems:'center',gap:8},name:{flex:1,color:colors.text,fontSize:20,fontWeight:'800'},arrow:{color:colors.cyan,fontSize:34,lineHeight:30},meta:{flexDirection:'row',gap:8},badge:{color:colors.ink,backgroundColor:colors.lime,paddingHorizontal:8,paddingVertical:4,borderRadius:7,fontSize:11,fontWeight:'900'},role:{color:colors.muted,paddingVertical:4,fontSize:12,fontWeight:'700'}});
