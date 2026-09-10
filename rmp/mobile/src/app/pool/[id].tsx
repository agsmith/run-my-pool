import { Redirect, Stack, router, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { Text, TextInput } from "react-native";
import { apiFetch } from "@/api/client";
import type { Pool } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { Screen } from "@/components/Screen";
import { Button, Card, LoadState, ui } from "@/components/NativeUI";
import { PoolBreakdown } from "@/components/PoolBreakdown";
import type { Breakdown } from "@/domain/survivor";
import { useResource } from "@/hooks/useResource";
export default function PoolScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status } = useAuth();
  const [password, setPassword] = useState("");
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState("");
  const resource = useResource(
    useCallback(async () => {
      const [access, mine] = await Promise.all([
        apiFetch<{ has_admin_access: boolean }>(`/pools/${id}/is-admin`),
        apiFetch<Pool[]>("/pools/my-pools"),
      ]);
      const member = access.has_admin_access || mine.some((p) => p.id === id);
      const pool = await apiFetch<Pool>(
        member ? `/pools/${id}` : `/pools/invite/${id}`,
      );
      let week: number | null = null;
      let rows: Breakdown[] | null = null;
      if (member && pool.pool_type === "survivor") {
        week = (
          await apiFetch<{ week: number }>(`/pools/${id}/activity-summary`)
        ).week;
        rows = await apiFetch<Breakdown[]>(
          `/picks/pool/${id}/week/${week}/breakdown`,
        );
      }
      return { pool, access, member, week, rows };
    }, [id]),
  );
  async function join() {
    setJoining(true);
    setError("");
    try {
      await apiFetch(`/pools/${id}/join`, {
        method: "POST",
        body: JSON.stringify({ password: password || null }),
      });
      await resource.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setJoining(false);
    }
  }
  if (status === "anonymous") return <Redirect href="/login" />;
  const d = resource.data;
  return (
    <Screen refreshing={resource.busy} onRefresh={resource.reload}>
      <Stack.Screen options={{ title: d?.pool.name || "Pool Home" }} />
      <LoadState
        busy={resource.busy}
        error={resource.error || error}
        empty={!d}
      />
      {d && (
        <>
          <Text style={ui.title}>{d.pool.name}</Text>
          <Text style={ui.copy}>
            {d.week ? `Week ${d.week} · ` : ""}Pool Home
          </Text>
          {d.member ? (
            <>
              <Button
                title="My entries & picks"
                onPress={() =>
                  router.push({
                    pathname:
                      d.pool.pool_type === "survivor"
                        ? "/survivor/[id]"
                        : d.pool.pool_type === "pickem"
                          ? "/pickem/[id]"
                          : "/squares/[id]",
                    params: { id },
                  })
                }
              />
              {d.rows && <PoolBreakdown rows={d.rows} />}
              <Button
                secondary
                title={
                  d.pool.pool_type === "squares"
                    ? "Results & payouts"
                    : "Leaderboard"
                }
                onPress={() =>
                  router.push({
                    pathname:
                      d.pool.pool_type === "squares"
                        ? "/squares/[id]"
                        : "/leaderboard/[id]",
                    params: { id },
                  })
                }
              />
              <Button
                secondary
                title="Forum"
                onPress={() =>
                  router.push({ pathname: "/forum/[id]", params: { id } })
                }
              />
              {d.access.has_admin_access && (
                <Button
                  secondary
                  title="Pool Admin"
                  onPress={() =>
                    router.push({ pathname: "/admin/[id]", params: { id } })
                  }
                />
              )}
            </>
          ) : (
            <Card>
              <Text style={ui.heading}>Join this pool</Text>
              {d.pool.is_private && (
                <TextInput
                  style={ui.input}
                  placeholder="Join code"
                  accessibilityLabel="Join code"
                  placeholderTextColor="#9ab0b3"
                  secureTextEntry
                  value={password}
                  onChangeText={setPassword}
                />
              )}
              <Button
                title={joining ? "Joining…" : "Join pool"}
                disabled={joining}
                onPress={join}
              />
            </Card>
          )}
        </>
      )}
    </Screen>
  );
}
