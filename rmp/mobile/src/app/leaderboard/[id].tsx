import { Stack, useLocalSearchParams } from "expo-router";
import { useCallback } from "react";
import { Text } from "react-native";
import { apiFetch } from "@/api/client";
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
export default function Leaderboard() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const r = useResource(
    useCallback(() => apiFetch<Row[]>(`/picks/pool/${id}/leaderboard`), [id]),
  );
  return (
    <Screen refreshing={r.busy} onRefresh={r.reload}>
      <Stack.Screen options={{ title: "Leaderboard" }} />
      <Text style={ui.title}>Leaderboard</Text>
      <Text style={ui.copy}>
        Standings include revealed picks only. Pull down for the latest results.
      </Text>
      <LoadState busy={r.busy} error={r.error} empty={!r.data} />
      {r.data?.length === 0 && <Text style={ui.copy}>No entries yet.</Text>}
      {r.data?.map((row) => (
        <Card key={row.entry_id}>
          <Text style={ui.heading}>
            #{row.rank} · {row.entry_name}
          </Text>
          <Text style={ui.copy}>
            {row.user_display_name} · {row.alive ? "Active" : "Eliminated"}
          </Text>
          <Text style={ui.success}>
            {row.correct_picks} {row.correct_picks === 1 ? "win" : "wins"} ·{" "}
            {row.completed_picks} completed
          </Text>
          {row.picks.map((p, i) => (
            <Text key={`${p.week}-${i}`} style={ui.text}>
              Week {p.week} · {p.team} ·{" "}
              {p.result === "win"
                ? "Win"
                : p.result === "loss"
                  ? "Loss"
                  : "Pending"}
            </Text>
          ))}
        </Card>
      ))}
    </Screen>
  );
}
