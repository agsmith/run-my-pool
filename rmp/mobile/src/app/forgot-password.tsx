import { Stack } from "expo-router";
import { useState } from "react";
import { Text, TextInput } from "react-native";
import { apiFetch } from "@/api/client";
import { Screen } from "@/components/Screen";
import { Button, ui } from "@/components/NativeUI";
export default function Recovery() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function send() {
    setBusy(true);
    try {
      await apiFetch("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      setMessage(
        "If that email has an account, password reset instructions are on their way.",
      );
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Screen>
      <Stack.Screen options={{ title: "Reset password" }} />
      <Text style={ui.title}>Forgot your password?</Text>
      <Text style={ui.copy}>
        Enter your account email to receive reset instructions.
      </Text>
      <TextInput
        accessibilityLabel="Email"
        autoCapitalize="none"
        keyboardType="email-address"
        style={ui.input}
        value={email}
        onChangeText={setEmail}
      />
      <Button
        title={busy ? "Sending…" : "Send reset instructions"}
        disabled={busy || !email.trim()}
        onPress={send}
      />
      {!!message && (
        <Text accessibilityRole="alert" style={ui.text}>
          {message}
        </Text>
      )}
    </Screen>
  );
}
