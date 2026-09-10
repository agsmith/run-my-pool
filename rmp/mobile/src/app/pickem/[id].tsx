import { TeamHelmet } from "@/components/TeamHelmet";
import { Stack, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { Text, TextInput, View } from "react-native";
import { apiFetch } from "@/api/client";
import type { Pool } from "@/api/types";
import type { Entry, Game, Pick, WeekLock } from "@/domain/survivor";
import { Screen } from "@/components/Screen";
import { Button, Card, LoadState, ui } from "@/components/NativeUI";
import { useResource } from "@/hooks/useResource";
type GamePick = Pick & { game_id: number };
export default function PickEm() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [week, setWeek] = useState<number | null>(null);
  const [entryId, setEntryId] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [total, setTotal] = useState("");
  const r = useResource(
    useCallback(async () => {
      const selectedWeek =
        week ??
        (await apiFetch<{ week: number }>(`/pools/${id}/activity-summary`))
          .week;
      const [pool, entries, games, locks] = await Promise.all([
        apiFetch<Pool>(`/pools/${id}`),
        apiFetch<Entry[]>(`/entries/pool/${id}`),
        apiFetch<Game[]>(`/schedule/week/${selectedWeek}`),
        apiFetch<{ weeks: Record<string, WeekLock> }>(
          `/pools/${id}/lock-status`,
        ),
      ]);
      const selectedEntry = entries.find((e) => e.id === entryId) || entries[0];
      const picks = selectedEntry
        ? await apiFetch<GamePick[]>(`/picks/entry/${selectedEntry.id}`)
        : [];
      const tiebreaker =
        selectedEntry && pool.pickem_slate === "sunday_monday"
          ? await apiFetch<{ predicted_total: number; locked: boolean } | null>(
              `/picks/entry/${selectedEntry.id}/tiebreaker/${selectedWeek}`,
            )
          : null;
      return {
        pool,
        entries,
        games,
        week: selectedWeek,
        entry: selectedEntry,
        picks,
        lock: locks.weeks[String(selectedWeek)],
        tiebreaker,
      };
    }, [id, week, entryId]),
  );
  async function mutate(
    path: string,
    method: string,
    body: unknown,
    message: string,
  ) {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await apiFetch(path, { method, body: JSON.stringify(body) });
      setNotice(message);
      await r.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const d = r.data;
  const games =
    d?.games.filter((g) => {
      const day = new Intl.DateTimeFormat("en-US", {
        weekday: "short",
        timeZone: "America/New_York",
      }).format(new Date(g.start_time));
      return (
        !d.pool.pickem_slate ||
        d.pool.pickem_slate === "all" ||
        (d.pool.pickem_slate === "sunday"
          ? day === "Sun"
          : ["Sun", "Mon"].includes(day))
      );
    }) || [];
  const picks = d?.picks.filter((p) => p.week === d.week) || [];
  const target = Math.min(
    d?.pool.pickem_games_per_week || games.length,
    games.length,
  );
  const poolLocked =
    !d?.lock ||
    d.lock.locked ||
    !!(d.lock.deadline && Date.parse(d.lock.deadline) <= Date.now());
  return (
    <Screen refreshing={r.busy} onRefresh={r.reload}>
      <Stack.Screen options={{ title: "Pick ’Em" }} />
      <Text style={ui.title}>Weekly Picks</Text>
      <LoadState busy={r.busy} error={error || r.error} empty={!d} />
      {!!notice && (
        <Text accessibilityLiveRegion="polite" style={ui.success}>
          {notice}
        </Text>
      )}
      {d && (
        <>
          <View style={ui.row}>
            <Button
              secondary
              title="Previous"
              disabled={d.week <= 1 || busy}
              onPress={() => {
                setWeek(d.week - 1);
                setTotal("");
              }}
            />
            <Text style={ui.heading}>Week {d.week}</Text>
            <Button
              secondary
              title="Next"
              disabled={d.week >= 18 || busy}
              onPress={() => {
                setWeek(d.week + 1);
                setTotal("");
              }}
            />
          </View>
          {d.entries.map((e) => (
            <Button
              key={e.id}
              secondary={e.id !== d.entry?.id}
              title={e.name}
              onPress={() => {
                setEntryId(e.id);
                setTotal("");
              }}
            />
          ))}
          {d.entry && (
            <>
              <Text style={picks.length < target ? ui.success : ui.copy}>
                {picks.length}/{target} picks saved
                {picks.length < target
                  ? ` · ${target - picks.length} still needed`
                  : " · Complete"}
              </Text>
              {games.map((g) => {
                const current = picks.find((p) => p.game_id === g.game_id);
                const locked =
                  poolLocked ||
                  current?.locked ||
                  Date.parse(g.start_time) <= Date.now();
                const full = picks.length >= target && !current;
                return (
                  <View
                    key={g.game_id}
                    style={[
                      ui.card,
                      !current && !locked && !full && ui.attention,
                    ]}
                  >
                    <View style={ui.row}>
                      <TeamHelmet team={g.away_team.abbrv} />
                      <Text style={ui.copy}>at</Text>
                      <TeamHelmet team={g.home_team.abbrv} />
                    </View>
                    <Text style={ui.heading}>
                      {g.away_team.abbrv} at {g.home_team.abbrv}
                    </Text>
                    <Text style={ui.copy}>
                      {new Date(g.start_time).toLocaleString()}
                    </Text>
                    <Text
                      style={locked ? ui.copy : current ? ui.copy : ui.success}
                    >
                      {locked
                        ? "Locked"
                        : current
                          ? `Saved: ${current.team}`
                          : full
                            ? "Weekly limit reached"
                            : "Needs attention · choose a team"}
                    </Text>
                    {[g.away_team, g.home_team].map((t) => (
                      <Button
                        key={t.id}
                        title={`${current?.team === t.abbrv ? "✓ Saved · " : current ? "Change to " : ""}${t.name}`}
                        secondary={!!current || locked || full}
                        disabled={busy || locked || full}
                        onPress={() => {
                          if (Date.parse(g.start_time) <= Date.now()) {
                            setError(
                              "This game has started. Picks are locked.",
                            );
                            return;
                          }
                          void mutate(
                            "/picks/create",
                            "POST",
                            {
                              entry_id: d.entry.id,
                              week: d.week,
                              game_id: g.game_id,
                              team: t.abbrv,
                            },
                            `${t.abbrv} saved.`,
                          );
                        }}
                      />
                    ))}
                    {current && !locked && (
                      <Button
                        secondary
                        title="Remove pick"
                        disabled={busy}
                        onPress={() =>
                          mutate(
                            `/picks/${current.id}`,
                            "DELETE",
                            undefined,
                            "Pick removed.",
                          )
                        }
                      />
                    )}
                  </View>
                );
              })}
              {d.pool.pickem_slate === "sunday_monday" && (
                <Card>
                  <Text style={ui.heading}>Monday night tiebreaker</Text>
                  <Text style={ui.copy}>
                    Predict the combined score of the final Monday game.{" "}
                    {d.tiebreaker
                      ? `Saved: ${d.tiebreaker.predicted_total}`
                      : "No prediction saved."}
                  </Text>
                  <TextInput
                    accessibilityLabel="Combined score"
                    keyboardType="number-pad"
                    style={ui.input}
                    value={total}
                    onChangeText={setTotal}
                    placeholder="0–200"
                    placeholderTextColor="#9ab0b3"
                  />
                  <Button
                    title="Save tiebreaker"
                    disabled={
                      busy ||
                      poolLocked ||
                      d.tiebreaker?.locked ||
                      (!d.lock?.deadline &&
                        games.some(
                          (g) => Date.parse(g.start_time) <= Date.now(),
                        )) ||
                      total.trim() === "" ||
                      !Number.isInteger(Number(total)) ||
                      Number(total) < 0 ||
                      Number(total) > 200
                    }
                    onPress={() =>
                      mutate(
                        `/picks/entry/${d.entry.id}/tiebreaker`,
                        "PUT",
                        { week: d.week, predicted_total: Number(total) },
                        "Tiebreaker saved.",
                      )
                    }
                  />
                </Card>
              )}
            </>
          )}
          <Card>
            <Text style={ui.heading}>Add an entry</Text>
            <TextInput
              accessibilityLabel="Entry name"
              style={ui.input}
              value={name}
              onChangeText={setName}
            />
            <Button
              title="Create entry"
              disabled={busy || !name.trim()}
              onPress={() =>
                mutate(
                  "/entries/create",
                  "POST",
                  { pool_id: id, name: name.trim() },
                  "Entry created.",
                )
              }
            />
          </Card>
        </>
      )}
    </Screen>
  );
}
