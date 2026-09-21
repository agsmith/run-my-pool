import { useCallback, useState } from "react";
import { Text, View } from "react-native";
import { Redirect, Stack, useLocalSearchParams } from "expo-router";
import { apiFetch } from "@/api/client";
import type { Pool } from "@/api/types";
import type { Breakdown, PickEmWeeklyStanding, WeekLock } from "@/domain/survivor";
import { Screen } from "@/components/Screen";
import { Button, LoadState, ui } from "@/components/NativeUI";
import { PoolBreakdown } from "@/components/PoolBreakdown";
import { useAuth } from "@/auth/AuthContext";
import { useResource } from "@/hooks/useResource";

export default function BreakdownScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status } = useAuth();
  const [week, setWeek] = useState<number | null>(null);
  const resource = useResource(
    useCallback(async () => {
      const selectedWeek =
        week ?? (await apiFetch<{ week: number }>(`/pools/${id}/activity-summary`)).week;
      const pool = await apiFetch<Pool>(`/pools/${id}`);
      const [locks, rows, standings] = await Promise.all([
        apiFetch<{ weeks: Record<string, WeekLock> }>(`/pools/${id}/lock-status`),
        apiFetch<Breakdown[]>(`/picks/pool/${id}/week/${selectedWeek}/breakdown`),
        pool.pool_type === "pickem"
          ? apiFetch<PickEmWeeklyStanding[]>(`/picks/pool/${id}/weekly-standings/${selectedWeek}`)
          : Promise.resolve([] as PickEmWeeklyStanding[]),
      ]);
      return {
        pool,
        week: selectedWeek,
        lock: locks.weeks[String(selectedWeek)],
        rows,
        standings,
      };
    }, [id, week]),
  );
  if (status === "anonymous") return <Redirect href="/login" />;
  const d = resource.data;
  const locked =
    !!d?.lock &&
    (d.lock.locked ||
      !!(d.lock.deadline && Date.parse(d.lock.deadline) <= Date.now()));
  return (
    <Screen refreshing={resource.busy} onRefresh={resource.reload}>
      <Stack.Screen options={{ title: "Weekly Pick Breakdown" }} />
      <Text style={ui.title}>Weekly Pick Breakdown</Text>
      <Text style={ui.copy}>
        View each pool member’s picks after the weekly lock.
      </Text>
      <LoadState busy={resource.busy} error={resource.error} empty={!d} />
      {d && (
        <>
          <View style={ui.row}>
            <Button
              secondary
              title="Previous"
              disabled={d.week <= 1}
              onPress={() => setWeek(d.week - 1)}
            />
            <Text style={ui.heading}>Week {d.week}</Text>
            <Button
              secondary
              title="Next"
              disabled={d.week >= 18}
              onPress={() => setWeek(d.week + 1)}
            />
          </View>
          <View style={ui.row}>
            {Array.from({ length: 18 }, (_, index) => index + 1).map((value) => (
              <Button
                key={value}
                secondary={value !== d.week}
                selected={value === d.week}
                title={String(value)}
                onPress={() => setWeek(value)}
              />
            ))}
          </View>
          {locked ? (
            <PoolBreakdown rows={d.rows} poolType={d.pool.pool_type === "pickem" ? "pickem" : "survivor"} standings={d.standings} />
          ) : (
            <Text style={ui.copy}>This week’s picks will appear after the weekly lock.</Text>
          )}
        </>
      )}
    </Screen>
  );
}
