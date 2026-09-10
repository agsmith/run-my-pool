import { TeamHelmet } from "@/components/TeamHelmet";
import { Redirect, Stack, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { colors } from "@/theme";
import { PoolBreakdown } from "@/components/PoolBreakdown";
import {
  Breakdown,
  Entry,
  Game,
  Pick,
  WeekLock,
  pickLocked,
  unavailable,
} from "@/domain/survivor";

type Board = {
  entries: Entry[];
  picks: Record<string, Pick[]>;
  games: Game[];
  lock: WeekLock;
  breakdown: Breakdown[];
};
export default function SurvivorScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status } = useAuth();
  const [week, setWeek] = useState<number | null>(null);
  const [board, setBoard] = useState<Board | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pickerError, setPickerError] = useState("");
  const [notice, setNotice] = useState("");
  const [entry, setEntry] = useState<Entry | null>(null);
  const [selection, setSelection] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [now, setNow] = useState(Date.now());
  const request = useRef(0);
  const mutation = useRef(false);
  const load = useCallback(async () => {
    if (status !== "authenticated" || !id) return;
    const version = ++request.current;
    setBusy(true);
    setError("");
    try {
      const selectedWeek =
        week ??
        (await apiFetch<{ week: number }>(`/pools/${id}/activity-summary`))
          .week;
      if (
        !Number.isInteger(selectedWeek) ||
        selectedWeek < 1 ||
        selectedWeek > 18
      )
        throw new Error("Choose a week to load your entries.");
      if (week === null) {
        if (version === request.current) setWeek(selectedWeek);
        return;
      }
      const [entries, games, locks, breakdown] = await Promise.all([
        apiFetch<Entry[]>(`/entries/pool/${id}`),
        apiFetch<Game[]>(`/schedule/week/${selectedWeek}`),
        apiFetch<{ weeks: Record<string, WeekLock> }>(
          `/pools/${id}/lock-status`,
        ),
        apiFetch<Breakdown[]>(
          `/picks/pool/${id}/week/${selectedWeek}/breakdown`,
        ),
      ]);
      if (!locks.weeks[String(selectedWeek)])
        throw new Error(
          "Lock status unavailable. Pull to refresh before picking.",
        );
      const picks = Object.fromEntries(
        await Promise.all(
          entries.map(async (row) => [
            row.id,
            await apiFetch<Pick[]>(`/picks/entry/${row.id}`),
          ]),
        ),
      );
      if (version === request.current) {
        setBoard({
          entries,
          games,
          picks,
          breakdown,
          lock: locks.weeks[String(selectedWeek)],
        });
        setNow(Date.now());
      }
    } catch (e) {
      if (version === request.current) {
        setBoard(null);
        setError(e instanceof Error ? e.message : "Unable to load picks");
      }
    } finally {
      if (version === request.current) setBusy(false);
    }
  }, [id, week, status]);
  useEffect(() => {
    void load();
    return () => {
      ++request.current;
    };
  }, [load]);
  // Update local lock labels at the deadline without refreshing server data.
  useEffect(() => {
    const next = [
      ...(board?.games.map((g) => Date.parse(g.start_time)) || []),
      Date.parse(board?.lock.deadline || ""),
    ]
      .filter((t) => t > Date.now())
      .sort((a, b) => a - b)[0];
    if (!next) return;
    const timer = setTimeout(
      () => setNow(Date.now()),
      Math.min(next - Date.now() + 50, 2147483647),
    );
    return () => clearTimeout(timer);
  }, [board, now]);
  const picks = entry && board ? board.picks[entry.id] || [] : [];
  const reason =
    selection && board && week
      ? unavailable(selection, week, picks, board.games, board.lock, now)
      : null;
  async function save() {
    if (!selection || !entry || !week || !board || mutation.current) return;
    const blocked = unavailable(
      selection,
      week,
      picks,
      board.games,
      board.lock,
      Date.now(),
    );
    if (blocked) {
      setPickerError(blocked);
      return;
    }
    mutation.current = true;
    setSaving(true);
    setPickerError("");
    try {
      await apiFetch("/picks/create", {
        method: "POST",
        body: JSON.stringify({ entry_id: entry.id, week, team: selection }),
      });
      setNotice(`${selection} saved for ${entry.name}, week ${week}.`);
      setEntry(null);
      setSelection(null);
      await load();
    } catch (e) {
      setPickerError(
        e instanceof Error
          ? e.message
          : "Could not save your pick. Refresh before retrying.",
      );
    } finally {
      mutation.current = false;
      setSaving(false);
    }
  }
  async function createEntry() {
    if (!name.trim() || mutation.current) return;
    mutation.current = true;
    setSaving(true);
    setError("");
    try {
      await apiFetch("/entries/create", {
        method: "POST",
        body: JSON.stringify({ pool_id: id, name: name.trim() }),
      });
      setName("");
      setNotice("Entry created. Choose a team below.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create entry");
    } finally {
      mutation.current = false;
      setSaving(false);
    }
  }
  if (status === "anonymous") return <Redirect href="/login" />;
  return (
    <SafeAreaView style={s.screen} edges={["bottom"]}>
      <Stack.Screen options={{ title: "Survivor picks" }} />
      <ScrollView
        contentContainerStyle={s.content}
        keyboardShouldPersistTaps="handled" automaticallyAdjustKeyboardInsets
        refreshControl={
          <RefreshControl
            refreshing={busy}
            onRefresh={load}
            tintColor={colors.lime}
          />
        }
      >
        <Text style={s.kicker}>YOUR WEEKLY BOARD</Text>
        <Text style={s.title}>Make your pick.</Text>
        <Text style={s.copy}>
          One team per entry. Picks lock at game kickoff or the pool deadline,
          whichever comes first.
        </Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={s.weeks}
        >
          {Array.from({ length: 18 }, (_, i) => i + 1).map((value) => (
            <Pressable
              key={value}
              accessibilityRole="button"
              accessibilityState={{ selected: week === value }}
              accessibilityLabel={`Week ${value}`}
              style={[s.week, week === value && s.selected]}
              onPress={() => {
                ++request.current;
                setBoard(null);
                setWeek(value);
                setNotice("");
              }}
            >
              <Text style={week === value ? s.dark : s.text}>{value}</Text>
            </Pressable>
          ))}
        </ScrollView>
        {!!error && (
          <Text accessibilityRole="alert" style={s.error}>
            {error}
          </Text>
        )}
        {!!notice && (
          <Text accessibilityLiveRegion="polite" style={s.success}>
            {notice}
          </Text>
        )}
        {!board && busy && <ActivityIndicator color={colors.lime} />}
        {!board && !busy && (
          <Pressable accessibilityRole="button" onPress={load} style={s.button}>
            <Text style={s.dark}>Retry</Text>
          </Pressable>
        )}
        {board && (
          <>
            <Text style={s.heading}>Week {week} · My entries</Text>
            {board.entries.map((row) => {
              const current = board.picks[row.id]?.find((p) => p.week === week);
              const locked = pickLocked(current, board.games, board.lock, now);
              const hasEligibleTeam = board.games.some((game) =>
                [game.home_team, game.away_team].some(
                  (team) =>
                    !unavailable(
                      team.abbrv,
                      week!,
                      board.picks[row.id] || [],
                      board.games,
                      board.lock,
                      now,
                    ),
                ),
              );
              return (
                <View
                  style={[
                    s.card,
                    !current &&
                      row.alive &&
                      !locked &&
                      hasEligibleTeam &&
                      s.attention,
                  ]}
                  key={row.id}
                >
                  <Text style={s.heading}>{row.name}</Text>
                  {current && <TeamHelmet team={current.team} size={60} />}
                  <Text style={s.copy}>
                    {!row.alive
                      ? "Eliminated"
                      : current
                        ? `${current.team} · ${locked ? "Locked" : "Saved"}`
                        : locked
                          ? "Week locked · no pick"
                          : !hasEligibleTeam
                            ? "No eligible teams available"
                            : "Needs attention · choose a team"}
                  </Text>
                  <Pressable
                    accessibilityRole="button"
                    disabled={!row.alive || locked || !hasEligibleTeam}
                    accessibilityState={{
                      disabled: !row.alive || locked || !hasEligibleTeam,
                    }}
                    style={[
                      s.button,
                      (current || locked || !row.alive || !hasEligibleTeam) &&
                        s.changeButton,
                      (!row.alive || locked || !hasEligibleTeam) && s.disabled,
                    ]}
                    onPress={() => {
                      setEntry(row);
                      setSelection(current?.team || null);
                      setPickerError("");
                      setError("");
                    }}
                  >
                    <Text
                      style={
                        current || locked || !row.alive || !hasEligibleTeam
                          ? s.changeText
                          : s.dark
                      }
                    >
                      {!row.alive
                        ? "Eliminated"
                        : locked
                          ? "Locked"
                          : !hasEligibleTeam
                            ? "No eligible teams"
                            : current
                              ? "Change pick"
                              : "Choose team"}
                    </Text>
                  </Pressable>
                </View>
              );
            })}
            {!board.entries.length && (
              <Text style={s.copy}>Create your first entry below.</Text>
            )}
            {!board.games.length && (
              <Text style={s.copy}>
                Matchups have not been posted for this week.
              </Text>
            )}
            <View style={s.card}>
              <Text style={s.heading}>Add an entry</Text>
              <TextInput
                accessibilityLabel="Entry name"
                value={name}
                onChangeText={setName}
                placeholder="Entry name"
                placeholderTextColor={colors.muted}
                style={s.input}
                maxLength={100}
              />
              <Pressable
                accessibilityRole="button"
                disabled={saving || !name.trim()}
                onPress={createEntry}
                style={[s.button, (saving || !name.trim()) && s.disabled]}
              >
                <Text style={s.dark}>
                  {saving ? "Saving…" : "Create entry"}
                </Text>
              </Pressable>
            </View>
            <PoolBreakdown rows={board.breakdown} />
          </>
        )}
      </ScrollView>
      <Modal
        visible={!!entry}
        animationType="slide"
        presentationStyle="fullScreen"
        onRequestClose={() => {
          if (!saving) setEntry(null);
        }}
      >
        <SafeAreaProvider>
          <SafeAreaView style={s.screen}>
            <View style={s.modalHeader}>
              <Text style={s.heading}>
                Week {week} · {entry?.name}
              </Text>
              <Pressable
                accessibilityRole="button"
                onPress={() => {
                  if (!saving) setEntry(null);
                }}
                style={s.close}
              >
                <Text style={s.text}>Close</Text>
              </Pressable>
            </View>
            <ScrollView contentContainerStyle={s.content}>
              {board?.games.map((game) => (
                <View key={game.game_id} style={s.card}>
                  <Text style={s.copy}>
                    {new Date(game.start_time).toLocaleString([], {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                  </Text>
                  {[game.away_team, game.home_team].map((team) => {
                    const blocked = week
                      ? unavailable(
                          team.abbrv,
                          week,
                          picks,
                          board.games,
                          board.lock,
                          now,
                        )
                      : "Choose week";
                    return (
                      <Pressable
                        key={team.id}
                        accessibilityRole="button"
                        accessibilityState={{
                          disabled: !!blocked,
                          selected: selection === team.abbrv,
                        }}
                        disabled={!!blocked || saving}
                        onPress={() => {
                          setSelection(team.abbrv);
                          setPickerError("");
                        }}
                        style={[
                          s.team,
                          selection === team.abbrv && s.selected,
                          !!blocked && s.disabled,
                        ]}
                      >
                        <TeamHelmet team={team.abbrv} />
                        <Text
                          style={selection === team.abbrv ? s.dark : s.text}
                        >
                          {team.abbrv} · {team.name}
                        </Text>
                        {!!blocked && (
                          <Text
                            style={selection === team.abbrv ? s.dark : s.copy}
                          >
                            {blocked}
                          </Text>
                        )}
                      </Pressable>
                    );
                  })}
                </View>
              ))}
            </ScrollView>
            <View style={s.footer}>
              {!!(pickerError || error || reason) && (
                <Text
                  accessibilityRole="alert"
                  accessibilityLiveRegion="assertive"
                  style={s.error}
                >
                  {pickerError || error || reason}
                </Text>
              )}

              <Pressable
                accessibilityRole="button"
                disabled={!selection || !!reason || saving || !board}
                style={[
                  s.button,
                  (!selection || !!reason || saving || !board) && s.disabled,
                ]}
                onPress={save}
              >
                <Text style={s.dark}>
                  {saving
                    ? "Saving…"
                    : selection
                      ? `Confirm ${selection}`
                      : "Choose a team"}
                </Text>
              </Pressable>
            </View>
          </SafeAreaView>
        </SafeAreaProvider>
      </Modal>
    </SafeAreaView>
  );
}
const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.ink },
  content: { padding: 20, gap: 16 },
  kicker: { color: colors.lime, fontWeight: "900", letterSpacing: 2 },
  title: { color: colors.text, fontSize: 34, fontWeight: "900" },
  heading: {
    color: colors.text,
    fontSize: 20,
    fontWeight: "800",
    flexShrink: 1,
  },
  copy: { color: colors.muted, fontSize: 16, lineHeight: 23 },
  text: { color: colors.text, fontSize: 16, fontWeight: "700" },
  dark: { color: colors.ink, fontSize: 16, fontWeight: "800" },
  weeks: { gap: 8 },
  week: {
    minWidth: 48,
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.panel,
    borderRadius: 12,
  },
  selected: { backgroundColor: colors.lime },
  card: {
    backgroundColor: colors.panel,
    borderRadius: 16,
    padding: 16,
    gap: 12,
  },
  button: {
    minHeight: 50,
    padding: 14,
    borderRadius: 12,
    backgroundColor: colors.lime,
    alignItems: "center",
    justifyContent: "center",
  },
  attention: { borderWidth: 1, borderColor: colors.lime },
  changeButton: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.cyan,
  },
  changeText: { color: colors.cyan, fontSize: 16, fontWeight: "800" },
  disabled: { opacity: 0.45 },
  error: { color: colors.danger, fontSize: 16, lineHeight: 22 },
  success: { color: colors.lime, fontSize: 16 },
  input: {
    minHeight: 50,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    padding: 12,
    color: colors.text,
    fontSize: 16,
  },
  modalHeader: {
    padding: 20,
    gap: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomWidth: 1,
    borderColor: colors.line,
  },
  close: { minHeight: 44, justifyContent: "center", padding: 8 },
  team: {
    padding: 16,
    minHeight: 64,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 12,
    gap: 6,
  },
  footer: {
    padding: 16,
    gap: 8,
    borderTopWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.panel,
  },
});
