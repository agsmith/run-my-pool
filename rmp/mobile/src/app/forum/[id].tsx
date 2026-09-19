import { apiTime } from "@/domain/time";
import { Stack, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { Alert, Linking, Text, TextInput } from "react-native";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { Screen } from "@/components/Screen";
import { Button, Card, LoadState, ui } from "@/components/NativeUI";
import { fetchAllForumMessages } from "@/domain/forum";
import { useResource } from "@/hooks/useResource";

type Message = {
  id: string;
  user_id: string;
  user_display_name: string;
  message: string;
  created_at: string;
};
type Safety = {
  suspended: boolean;
  blocks: { id: string; name: string }[];
};
const reasons = [
  "Harassment or hate",
  "Threats or violence",
  "Sexual content",
  "Spam or scam",
  "Personal information",
  "Other",
];

export default function Forum() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reporting, setReporting] = useState<string | null>(null);
  const r = useResource(
    useCallback(async () => {
      const [messages, safety] = await Promise.all([
        fetchAllForumMessages((skip, limit) =>
          apiFetch<Message[]>(
            `/messages/pool/${id}?skip=${skip}&limit=${limit}`,
          ),
        ),
        apiFetch<Safety>(`/messages/pool/${id}/safety`),
      ]);
      return { messages, safety };
    }, [id]),
  );
  async function mutate(
    path: string,
    method: string,
    body?: unknown,
    success = "Updated.",
  ) {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await apiFetch(path, {
        method,
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      if (path === `/messages/pool/${id}` && method === "POST") setText("");
      setReporting(null);
      setNotice(success);
      await r.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function confirm(title: string, explanation: string, action: () => void) {
    Alert.alert(title, explanation, [
      { text: "Cancel", style: "cancel" },
      { text: "Confirm", style: "destructive", onPress: action },
    ]);
  }
  const safety = r.data?.safety;
  return (
    <Screen refreshing={r.busy} onRefresh={r.reload}>
      <Stack.Screen options={{ title: "Forum" }} />
      <Text style={ui.title}>Pool Forum</Text>
      <Card>
        <Text style={ui.heading}>Keep the conversation respectful</Text>
        <Text style={ui.copy}>
          No harassment, hate speech, threats, explicit content, scams, spam, or
          sharing someone’s private information. Posting filters are a first
          check; report anything they miss. Reports go to pool and platform
          moderators.
        </Text>
        <Text selectable style={ui.copy}>
          Questions, urgent reports, or appeals: support@runmypool.net
        </Text>
        <Button
          secondary
          title="Contact support"
          onPress={() =>
            Linking.openURL(
              "mailto:support@runmypool.net?subject=Forum%20safety",
            ).catch(() =>
              setError(
                "No email app is available. Email support@runmypool.net.",
              ),
            )
          }
        />
      </Card>
      <LoadState busy={r.busy} error={error || r.error} empty={!r.data} />
      {!!notice && (
        <Text accessibilityLiveRegion="polite" style={ui.success}>
          {notice}
        </Text>
      )}
      {safety?.suspended ? (
        <Text style={ui.copy}>
          Your posting access in this pool is suspended. Contact support to
          appeal.
        </Text>
      ) : (
        r.data && (
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
            <Text style={ui.copy}>
              {text.length}/250 · By posting, you agree to the Forum rules
              above.
            </Text>
            <Button
              title={busy ? "Working…" : "Post message"}
              disabled={busy || !text.trim()}
              onPress={() =>
                mutate(
                  `/messages/pool/${id}`,
                  "POST",
                  { message: text.trim() },
                  "Message posted.",
                )
              }
            />
          </Card>
        )
      )}
      {!!safety?.blocks.length && (
        <Card>
          <Text style={ui.heading}>Blocked members</Text>
          <Text style={ui.copy}>
            Their messages are hidden from you across all pool forums.
          </Text>
          {safety.blocks.map((b) => (
            <Button
              key={b.id}
              secondary
              disabled={busy}
              title={`Unblock ${b.name}`}
              onPress={() => mutate(`/messages/blocks/${b.id}`, "DELETE")}
            />
          ))}
        </Card>
      )}
      {r.data?.messages.length === 0 && (
        <Text style={ui.copy}>No visible messages yet.</Text>
      )}
      {r.data?.messages.map((m) => (
        <Card key={m.id}>
          <Text style={ui.heading}>{m.user_display_name}</Text>
          <Text style={ui.copy}>
            {new Date(apiTime(m.created_at)).toLocaleString()}
          </Text>
          <Text style={ui.text}>{m.message}</Text>
          {m.user_id === user?.id && (
            <Button
              secondary
              disabled={busy}
              title="Delete message"
              onPress={() =>
                confirm(
                  "Delete message?",
                  "This removes the message from the pool forum.",
                  () => mutate(`/messages/${m.id}`, "DELETE"),
                )
              }
            />
          )}
          {m.user_id !== user?.id && (
            <>
              <Button
                secondary
                disabled={busy}
                title="Report message"
                onPress={() => setReporting(reporting === m.id ? null : m.id)}
              />
              {reporting === m.id && (
                <>
                  <Text style={ui.copy}>
                    Choose a reason. The message will be hidden from you and
                    sent for moderator review.
                  </Text>
                  {reasons.map((reason) => (
                    <Button
                      key={reason}
                      secondary
                      disabled={busy}
                      title={reason}
                      onPress={() =>
                        mutate(
                          `/messages/${m.id}/report`,
                          "POST",
                          { reason },
                          "Report received. The message is hidden from you and queued for moderator review.",
                        )
                      }
                    />
                  ))}
                  <Button
                    secondary
                    title="Cancel report"
                    onPress={() => setReporting(null)}
                  />
                </>
              )}
              <Button
                secondary
                disabled={busy}
                title="Block member"
                onPress={() =>
                  confirm(
                    "Block member?",
                    "Hide this member’s posts from you in all pool forums. You can unblock them above.",
                    () =>
                      mutate(
                        `/messages/pool/${id}/blocks/${m.user_id}`,
                        "PUT",
                        undefined,
                        "Member blocked.",
                      ),
                  )
                }
              />
            </>
          )}
        </Card>
      ))}
    </Screen>
  );
}
