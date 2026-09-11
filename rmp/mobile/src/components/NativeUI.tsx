import { PropsWithChildren } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { colors } from "@/theme";
export const ui = StyleSheet.create({
  title: { color: colors.text, fontSize: 30, fontWeight: "900" },
  heading: { color: colors.text, fontSize: 20, fontWeight: "800" },
  text: { color: colors.text, fontSize: 16, lineHeight: 24 },
  copy: { color: colors.muted, fontSize: 15, lineHeight: 22 },
  card: {
    backgroundColor: colors.panel,
    borderRadius: 16,
    padding: 16,
    gap: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    padding: 14,
    minHeight: 50,
    color: colors.text,
    fontSize: 16,
  },
  row: {
    flexDirection: "row",
    gap: 10,
    alignItems: "center",
    flexWrap: "wrap",
  },
  error: { color: colors.danger, fontSize: 16, lineHeight: 23 },
  success: { color: colors.lime, fontSize: 16 },
  button: {
    minHeight: 50,
    padding: 14,
    borderRadius: 12,
    backgroundColor: colors.lime,
    alignItems: "center",
    justifyContent: "center",
  },
  outline: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.cyan,
  },
  buttonText: { color: colors.ink, fontWeight: "800", fontSize: 16 },
  secondaryText: { color: colors.cyan, fontWeight: "800", fontSize: 16 },
  pickBar: { padding: 12, borderRadius: 10, borderWidth: 1, borderColor: colors.line },
  pickWin: { backgroundColor: colors.panel, borderColor: "#62c98b", borderWidth: 2 },
  pickLoss: { backgroundColor: colors.panel, borderColor: "#f19aaf", borderWidth: 2 },
  pickWinText: { color: "#b9f6cf" },
  pickLossText: { color: "#ffd0dd" },
  attention: { borderWidth: 1, borderColor: colors.lime },
});
export function Button({
  title,
  onPress,
  disabled,
  secondary = false,
  result,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  secondary?: boolean;
  result?: string | null;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!disabled }}
      disabled={disabled}
      onPress={onPress}
      style={[
        ui.button,
        secondary && ui.outline,
        disabled && !result && { opacity: 0.45 },
        result === "win" && ui.pickWin,
        result === "loss" && ui.pickLoss,
      ]}
    >
      <Text style={[secondary ? ui.secondaryText : ui.buttonText, result === "win" && ui.pickWinText, result === "loss" && ui.pickLossText]}>{title}</Text>
    </Pressable>
  );
}
export function Card({ children }: PropsWithChildren) {
  return <View style={ui.card}>{children}</View>;
}
export function LoadState({
  busy,
  error,
  empty,
}: {
  busy: boolean;
  error: string;
  empty?: boolean;
}) {
  return (
    <>
      {busy && empty && <ActivityIndicator color={colors.lime} />}
      {!!error && (
        <Text accessibilityRole="alert" style={ui.error}>
          {error}
        </Text>
      )}
    </>
  );
}
