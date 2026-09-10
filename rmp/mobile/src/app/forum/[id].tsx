import { apiTime } from "@/domain/time";
import { Stack, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { Alert, Text, TextInput } from "react-native";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { Screen } from "@/components/Screen";
import { Button, Card, LoadState, ui } from "@/components/NativeUI";
import { useResource } from "@/hooks/useResource";
type Message = {
  id: string;
  user_id: string;
  user_display_name: string;
  message: string;
  created_at: string;
};
export default function Forum() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [limit, setLimit] = useState(50);
  const r = useResource(
    useCallback(
      () => apiFetch<Message[]>(`/messages/pool/${id}?limit=${limit}`),
      [id, limit],
    ),
  );
  async function post() {
    if (busy || !text.trim()) return;
    setBusy(true);
    setError("");
    try {
      const message = await apiFetch<Message>(`/messages/pool/${id}`, {
        method: "POST",
        body: JSON.stringify({ message: text.trim() }),
      });
      r.setData((rows) => [message, ...(rows || [])]);
      setText("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function remove(id: string) {
    Alert.alert(
      "Delete message?",
      "This removes your message from the pool forum.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            setBusy(true);
            try {
              await apiFetch(`/messages/${id}`, { method: "DELETE" });
              r.setData((rows) => rows?.filter((m) => m.id !== id) || []);
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          },
        },
      ],
    );
  }
  return (
    <Screen refreshing={r.busy} onRefresh={r.reload}>
      <Stack.Screen options={{ title: "Forum" }} />
      <Text style={ui.title}>Pool Forum</Text>
      <LoadState busy={r.busy} error={error || r.error} empty={!r.data} />
      {r.data && (
        <Card>
          <Text style={ui.heading}>Join the conversation</Text>
          <TextInput
            multiline
            maxLength={250}
            accessibilityLabel="Message"
            value={text}
            onChangeText={setText}
            style={[ui.input, { minHeight: 110, textAlignVertical: "top" }]}
          />
          <Text style={ui.copy}>{text.length}/250</Text>
          <Button
            title={busy ? "Sending…" : "Post message"}
            disabled={busy || !text.trim()}
            onPress={post}
          />
        </Card>
      )}
      {r.data?.length === 0 && (
        <Text style={ui.copy}>No messages yet. Start the conversation.</Text>
      )}
      {r.data?.map((m) => (
        <Card key={m.id}>
          <Text style={ui.heading}>{m.user_display_name}</Text>
          <Text style={ui.copy}>
            {new Date(apiTime(m.created_at)).toLocaleString()}
          </Text>
          <Text style={ui.text}>{m.message}</Text>
          {m.user_id === user?.id && (
            <Button
              secondary
              title="Delete message"
              disabled={busy}
              onPress={() => remove(m.id)}
            />
          )}
        </Card>
      ))}
      {r.data && r.data.length >= limit && (
        <Button
          secondary
          title="Older messages"
          onPress={() => setLimit((n) => n + 50)}
        />
      )}
    </Screen>
  );
}
