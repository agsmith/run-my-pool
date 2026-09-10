import { useCallback } from "react";
import { Text } from "react-native";
import { apiFetch } from "@/api/client";
import type { Pool } from "@/api/types";
import { PoolCard } from "@/components/PoolCard";
import { Screen } from "@/components/Screen";
import { LoadState, ui } from "@/components/NativeUI";
import { useResource } from "@/hooks/useResource";
export default function Pools() {
  const r = useResource(
    useCallback(() => apiFetch<Pool[]>("/pools/my-pools"), []),
  );
  return (
    <Screen refreshing={r.busy} onRefresh={r.reload}>
      <Text style={ui.title}>My Pools</Text>
      <LoadState busy={r.busy} error={r.error} empty={!r.data} />
      {r.data?.length === 0 && (
        <Text style={ui.copy}>
          No pools yet. Browse the directory to join a pool.
        </Text>
      )}
      {r.data?.map((p) => (
        <PoolCard key={p.id} pool={p} />
      ))}
    </Screen>
  );
}
