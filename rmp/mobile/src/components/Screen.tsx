import { PropsWithChildren } from 'react';
import { ScrollView, StyleSheet, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '@/theme';
export function Screen({ children, style }: PropsWithChildren<{ style?: ViewStyle }>) { return <SafeAreaView style={styles.safe} edges={['top']}><ScrollView contentContainerStyle={[styles.content, style]}>{children}</ScrollView></SafeAreaView>; }
const styles = StyleSheet.create({ safe: { flex: 1, backgroundColor: colors.ink }, content: { flexGrow: 1, padding: 20, gap: 16 } });
