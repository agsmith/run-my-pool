import { PropsWithChildren } from "react";
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@/theme";
export function Screen({
  children,
  style,
  refreshing = false,
  onRefresh,
}: PropsWithChildren<{
  style?: ViewStyle;
  refreshing?: boolean;
  onRefresh?: () => void;
}>) {
  return (
    <SafeAreaView style={styles.safe} edges={["bottom"]}>
      <ScrollView
        keyboardShouldPersistTaps="handled" automaticallyAdjustKeyboardInsets
        refreshControl={
          onRefresh ? (
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={colors.lime}
            />
          ) : undefined
        }
        contentContainerStyle={[styles.content, style]}
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.ink },
  content: { flexGrow: 1, padding: 20, gap: 16 },
});
