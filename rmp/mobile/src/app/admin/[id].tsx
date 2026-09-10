import { router, Stack, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Alert, Switch, Text, TextInput, View } from "react-native";
import { apiFetch } from "@/api/client";
import type { Pool } from "@/api/types";
import { Screen } from "@/components/Screen";
import { Button, Card, LoadState, ui } from "@/components/NativeUI";
import { useResource } from "@/hooks/useResource";
type Member = {
  id: string;
  email: string;
  total_entries: number;
  surviving_entries: number;
  picked_entries: number;
  is_admin: boolean;
  admin_role: string;
};
type Access = { has_admin_access: boolean; is_owner: boolean };
export default function Admin() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [privatePool, setPrivate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const r = useResource(
    useCallback(async () => {
      const access = await apiFetch<Access>(`/pools/${id}/is-admin`);
      if (!access.has_admin_access)
        throw new Error("Pool administrator access is required.");
      const [pool, overview, entries] = await Promise.all([
        apiFetch<Pool>(`/pools/${id}`),
        apiFetch<{ current_week: number; users: Member[] }>(
          `/admin/pools/${id}/users-overview`,
        ),
        apiFetch<{ id: string; user_id: string; locked: boolean }[]>(
          `/admin/pools/${id}/entries`,
        ),
      ]);
      return { access, pool, overview, entries };
    }, [id]),
  );
  useEffect(() => {
    if (r.data) {
      setName(r.data.pool.name);
      setDescription(r.data.pool.description || "");
      setPrivate(!!r.data.pool.is_private);
    }
  }, [r.data]);
  async function mutate(path: string, method: string, body?: unknown) {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await apiFetch(path, {
        method,
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      setNotice("Changes saved.");
      await r.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function confirm(title: string, copy: string, action: () => void) {
    Alert.alert(title, copy, [
      { text: "Cancel", style: "cancel" },
      { text: "Confirm", onPress: action },
    ]);
  }
  const d = r.data;
  return (
    <Screen refreshing={r.busy} onRefresh={r.reload}>
      <Stack.Screen options={{ title: "Pool Admin" }} />
      <Text style={ui.title}>Pool Admin</Text>
      <LoadState busy={r.busy} error={error || r.error} empty={!d} />
      {!!notice && (
        <Text accessibilityLiveRegion="polite" style={ui.success}>
          {notice}
        </Text>
      )}
      {d && (
        <>
          <Card>
            <Button secondary title="Forum moderation" onPress={() => router.push({ pathname: "/forum/[id]", params: { id } })} />
            <Text style={ui.heading}>Pool settings</Text>
            <Text style={ui.copy}>Pool name</Text>
            <TextInput
              accessibilityLabel="Pool name"
              value={name}
              onChangeText={setName}
              style={ui.input}
            />
            <Text style={ui.copy}>Description</Text>
            <TextInput
              multiline
              accessibilityLabel="Description"
              value={description}
              onChangeText={setDescription}
              style={ui.input}
            />
            <View style={ui.row}>
              <Text style={ui.text}>Private pool</Text>
              <Switch
                accessibilityLabel="Private pool"
                value={privatePool}
                onValueChange={setPrivate}
              />
            </View>
            {privatePool && (
              <TextInput
                accessibilityLabel="New join code"
                placeholder="New join code (leave blank to keep current)"
                placeholderTextColor="#9ab0b3"
                secureTextEntry
                value={joinCode}
                onChangeText={setJoinCode}
                style={ui.input}
              />
            )}
            <Button
              title="Save settings"
              disabled={busy || !name.trim()}
              onPress={() =>
                mutate(`/pools/${id}`, "PATCH", {
                  name: name.trim(),
                  description,
                  is_private: privatePool,
                  ...(privatePool && joinCode.trim()
                    ? { join_password: joinCode.trim() }
                    : {}),
                })
              }
            />
          </Card>
          {d.pool.pool_type === "survivor" && (
            <Card>
              <Text style={ui.heading}>Week {d.overview.current_week}</Text>
              <Text style={ui.copy}>
                Lock this week and apply the pool’s automatic-pick rules to
                missing selections.
              </Text>
              <Button
                secondary
                title="Lock week"
                disabled={busy}
                onPress={() =>
                  confirm(
                    "Lock this week?",
                    "Existing picks will lock and missing selections will be handled by the pool rules.",
                    () =>
                      mutate(
                        `/admin/pools/${id}/lock-week/${d.overview.current_week}`,
                        "POST",
                      ),
                  )
                }
              />
            </Card>
          )}
          <Text style={ui.heading}>Members · {d.overview.users.length}</Text>
          {d.overview.users.map((m) => {
            const locked = d.entries.some(
              (e) => e.user_id === m.id && e.locked,
            );
            return (
              <Card key={m.id}>
                <Text style={ui.text}>{m.email}</Text>
                <Text style={ui.copy}>
                  {m.admin_role} · {m.total_entries} entries
                </Text>
                {d.pool.pool_type === "survivor" && (
                  <Text
                    style={
                      m.surviving_entries > m.picked_entries
                        ? ui.success
                        : ui.copy
                    }
                  >
                    {m.picked_entries}/{m.surviving_entries} active entries have
                    picks
                  </Text>
                )}
                {m.admin_role !== "Owner" && (
                  <>
                    <Button
                      secondary
                      disabled={busy}
                      title={
                        locked ? "Unlock member picks" : "Lock member picks"
                      }
                      onPress={() =>
                        confirm(
                          locked ? "Unlock member?" : "Lock member?",
                          `This affects ${m.email} in this pool only.`,
                          () =>
                            mutate(
                              `/admin/pools/${id}/users/${m.id}/lock`,
                              locked ? "DELETE" : "POST",
                              locked
                                ? undefined
                                : { reason: "Locked by pool administrator" },
                            ),
                        )
                      }
                    />
                    {d.access.is_owner && (
                      <Button
                        secondary
                        disabled={busy}
                        title={
                          m.is_admin ? "Remove admin access" : "Make pool admin"
                        }
                        onPress={() =>
                          confirm(
                            "Change admin access?",
                            `Update pool administrator access for ${m.email}?`,
                            () =>
                              mutate(
                                `/admin/pools/${id}/admins${m.is_admin ? "?email=" + encodeURIComponent(m.email) : ""}`,
                                m.is_admin ? "DELETE" : "PUT",
                                m.is_admin ? undefined : { email: m.email },
                              ),
                          )
                        }
                      />
                    )}
                  </>
                )}
              </Card>
            );
          })}
        </>
      )}
    </Screen>
  );
}
