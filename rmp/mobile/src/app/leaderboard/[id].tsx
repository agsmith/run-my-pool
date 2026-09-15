import { Stack, useLocalSearchParams } from "expo-router";
import { useCallback } from "react";
import { Text, View } from "react-native";
import { apiFetch } from "@/api/client";
import type { Pool } from "@/api/types";
import { Screen } from "@/components/Screen";
import { Card, LoadState, ui } from "@/components/NativeUI";
import { useResource } from "@/hooks/useResource";
type Row = {
  rank: number;
  entry_id: string;
  entry_name: string;
  user_display_name: string;
  correct_picks: number;
  completed_picks: number;
  alive: boolean;
  picks: { week: number; team: string; result: string | null }[];
};
type PickEmRow = { user_id: string; user_display_name: string; points: number };
type PickEmBoardRow = PickEmRow & { rank: number };
export default function Leaderboard() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const r = useResource(
    useCallback(async () => {
      const pool = await apiFetch<Pool>(`/pools/${id}`);
      if (pool.pool_type !== "pickem") return { poolType: pool.pool_type, rows: await apiFetch<Row[]>(`/picks/pool/${id}/leaderboard`) };
      const source = await apiFetch<PickEmRow[]>(`/picks/pool/${id}/standings`);
      const byUser = new Map<string, { user_id: string; user_display_name: string; points: number }>();
      source.forEach((row) => {
        const current = byUser.get(row.user_id);
        if (current) current.points += row.points;
        else byUser.set(row.user_id, { user_id: row.user_id, user_display_name: row.user_display_name, points: row.points });
      });
      const rows: PickEmBoardRow[] = [...byUser.values()].sort((a, b) => b.points - a.points || a.user_display_name.localeCompare(b.user_display_name)).map((row, index) => ({ ...row, rank: index + 1 }));
      return { poolType: pool.pool_type, rows };
    }, [id]),
  );
  const pickem = r.data?.poolType === "pickem";
  const pickemRows = pickem ? (r.data?.rows as PickEmBoardRow[] | undefined) : undefined;
  const survivorRows = !pickem ? (r.data?.rows as Row[] | undefined) : undefined;
  const orderedSurvivorRows = survivorRows ? [...survivorRows].sort((a, b) => {
    if (a.alive !== b.alive) return a.alive ? -1 : 1;
    return a.entry_name.localeCompare(b.entry_name);
  }) : [];
  return (
    <Screen refreshing={r.busy} onRefresh={r.reload}>
      <Stack.Screen options={{ title: "Leaderboard" }} />
      <Text style={ui.title}>Leaderboard</Text>
      <Text style={ui.copy}>
        {pickem ? "Season points by member, highest total first." : "Standings include revealed picks only. Pull down for the latest results."}
      </Text>
      <LoadState busy={r.busy} error={r.error} empty={!r.data} />
      {r.data?.rows.length === 0 && <Text style={ui.copy}>No entries yet.</Text>}
      {pickem ? pickemRows?.map((row) => (
        <Card key={row.user_id}>
          <Text style={ui.heading}>#{row.rank} · {row.user_display_name}</Text>
          <Text style={ui.success}>{row.points} {row.points === 1 ? "point" : "points"}</Text>
        </Card>
      )) : orderedSurvivorRows.map((row) => {
        const lossWeek = row.picks.filter((pick) => pick.result === "loss").map((pick) => pick.week).sort((a, b) => a - b)[0];
        const throughWeek = row.picks.filter((pick) => pick.result === "win").reduce((max, pick) => Math.max(max, pick.week), 0);
        return (
        <View key={row.entry_id} style={[ui.card, row.alive ? s.survivorAlive : s.survivorEliminated]}>
          <Text style={ui.heading}>{row.entry_name}</Text>
          <Text style={ui.copy}>
            {row.user_display_name}
          </Text>
          <Text style={row.alive ? ui.success : ui.error}>
            {row.alive ? `Survive through Week ${throughWeek}` : `Eliminated Week ${lossWeek ?? "—"}`}
          </Text>
        </View>
        );
      })}
    </Screen>
  );
}
const s = {
  survivorAlive: { backgroundColor: "#102b1d", borderWidth: 2, borderColor: "#62c98b" },
  survivorEliminated: { backgroundColor: "#321b22", borderWidth: 2, borderColor: "#f19aaf" },
};
