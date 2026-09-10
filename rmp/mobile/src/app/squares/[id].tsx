import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { apiTime } from "@/domain/time";
import { Stack, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import type { Game } from "@/domain/survivor";
import { Screen } from "@/components/Screen";
import { Button, Card, LoadState, ui } from "@/components/NativeUI";
import { useResource } from "@/hooks/useResource";
import { colors } from "@/theme";
type Claim = {
  id: string;
  row_index: number;
  column_index: number;
  block_number: number;
  user_id: string;
  display_name: string;
};
type Board = {
  pool_name: string;
  game: Game;
  games: Game[];
  lock_time: string;
  locked: boolean;
  home_digits: number[] | null;
  away_digits: number[] | null;
  claims: Claim[];
  total_pot_cents: number | null;
  permissions: { is_admin: boolean; can_claim: boolean };
  payouts: {
    game_id: number;
    checkpoint: string;
    winner_display_name: string | null;
    amount_cents: number | null;
    home_score: number;
    away_score: number;
  }[];
};
export default function Squares() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const [name, setName] = useState(user?.display_name || "");
  const [cell, setCell] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const r = useResource(
    useCallback(() => apiFetch<Board>(`/squares/${id}`), [id]),
  );
  async function mutate(path: string, method: string, body?: unknown) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await apiFetch(path, {
        method,
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      setCell(null);
      setNotice("Board updated.");
      await r.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const d = r.data;
  const locked = !!d && (d.locked || apiTime(d.lock_time) <= Date.now());
  const claim = d?.claims.find((c) => c.block_number === cell);
  return (
    <Screen refreshing={r.busy} onRefresh={r.reload}>
      <Stack.Screen options={{ title: "Squares" }} />
      <Text style={ui.title}>Squares</Text>
      <LoadState busy={r.busy} error={error || r.error} empty={!d} />
      {!!notice && (
        <Text accessibilityLiveRegion="polite" style={ui.success}>
          {notice}
        </Text>
      )}
      {d && (
        <>
          <Text style={ui.heading}>{d.pool_name}</Text>
          {d.games.map((g) => (
            <Text key={g.game_id} style={ui.copy}>
              {g.away_team.name} at {g.home_team.name} ·{" "}
              {new Date(apiTime(g.start_time)).toLocaleString()}
            </Text>
          ))}
          <Text style={ui.copy}>
            {d.claims.length}/100 claimed · {locked ? "Locked" : "Open"}
            {d.total_pot_cents != null
              ? ` · $${(d.total_pot_cents / 100).toFixed(2)} pot`
              : ""}
          </Text>
          <Text style={ui.copy}>
            Swipe the board sideways to see all columns. Tap a square for its
            details. Numbers appear when the board locks.
          </Text>
          <ScrollView horizontal>
            <View style={{ gap: 4 }}>
              <Text style={ui.heading}>
                {d.game.away_team.abbrv} columns · {d.game.home_team.abbrv} rows
              </Text>
              <View style={{ flexDirection: "row", gap: 4 }}>
                <View style={{ width: 34 }} />
                {Array.from({ length: 10 }, (_, c) => (
                  <Text
                    key={c}
                    style={[ui.text, { width: 52, textAlign: "center" }]}
                  >
                    {d.away_digits?.[c] ?? "?"}
                  </Text>
                ))}
              </View>
              {Array.from({ length: 10 }, (_, row) => (
                <View
                  key={row}
                  style={{ flexDirection: "row", gap: 4, alignItems: "center" }}
                >
                  <Text style={[ui.text, { width: 34, textAlign: "center" }]}>
                    {d.home_digits?.[row] ?? "?"}
                  </Text>
                  {Array.from({ length: 10 }, (_, column) => {
                    const number = row * 10 + column + 1;
                    const owned = d.claims.find(
                      (c) => c.block_number === number,
                    );
                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityLabel={`Square ${number}, ${owned?.display_name || "available"}`}
                        accessibilityState={{ selected: cell === number }}
                        key={column}
                        onPress={() => setCell(number)}
                        style={{
                          width: 52,
                          height: 52,
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 6,
                          backgroundColor:
                            cell === number
                              ? colors.lime
                              : owned
                                ? colors.panelRaised
                                : colors.panel,
                          borderWidth: 1,
                          borderColor:
                            owned?.user_id === user?.id
                              ? colors.cyan
                              : colors.line,
                        }}
                      >
                        <Text
                          style={{
                            color: cell === number ? colors.ink : colors.text,
                            fontWeight: "800",
                          }}
                        >
                          {number}
                        </Text>
                        <Text
                          numberOfLines={1}
                          style={{
                            color: cell === number ? colors.ink : colors.muted,
                            fontSize: 10,
                            paddingHorizontal: 2,
                          }}
                        >
                          {owned?.display_name || "Open"}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>
              ))}
            </View>
          </ScrollView>
          {cell !== null && (
            <Modal
              visible
              animationType="slide"
              presentationStyle="pageSheet"
              onRequestClose={() => {
                if (!busy) setCell(null);
              }}
            >
              <SafeAreaProvider>
                <SafeAreaView style={{ flex: 1, backgroundColor: colors.ink }}>
                  <ScrollView
                    contentContainerStyle={{ padding: 20, gap: 16 }}
                    keyboardShouldPersistTaps="handled" automaticallyAdjustKeyboardInsets
                  >
                    <Button
                      secondary
                      title="Close"
                      disabled={busy}
                      onPress={() => setCell(null)}
                    />
                    <Card>
                      <Text style={ui.heading}>Square {cell}</Text>
                      {claim ? (
                        <>
                          <Text style={ui.text}>{claim.display_name}</Text>
                          {!locked &&
                            (claim.user_id === user?.id ||
                              d.permissions.is_admin) && (
                              <Button
                                secondary
                                title="Release square"
                                disabled={busy}
                                onPress={() =>
                                  Alert.alert(
                                    "Release square?",
                                    `Square ${cell} will become available.`,
                                    [
                                      { text: "Cancel", style: "cancel" },
                                      {
                                        text: "Release",
                                        style: "destructive",
                                        onPress: () =>
                                          mutate(
                                            `/squares/${id}/claims/${claim.id}`,
                                            "DELETE",
                                          ),
                                      },
                                    ],
                                  )
                                }
                              />
                            )}
                        </>
                      ) : locked ? (
                        <Text style={ui.copy}>
                          Board locked. New claims are closed.
                        </Text>
                      ) : (
                        <>
                          <TextInput
                            accessibilityLabel="Name on square"
                            maxLength={100}
                            style={ui.input}
                            value={name}
                            onChangeText={setName}
                            placeholder="Name on square"
                            placeholderTextColor={colors.muted}
                          />
                          <Button
                            title="Claim square"
                            disabled={
                              busy || !name.trim() || !d.permissions.can_claim
                            }
                            onPress={() =>
                              mutate(`/squares/${id}/claims`, "POST", {
                                row_index: Math.floor((cell - 1) / 10),
                                column_index: (cell - 1) % 10,
                                display_name: name.trim(),
                              })
                            }
                          />
                        </>
                      )}
                    </Card>
                  </ScrollView>
                </SafeAreaView>
              </SafeAreaProvider>
            </Modal>
          )}
          {d.permissions.is_admin && !locked && (
            <Button
              secondary
              title="Lock board & draw numbers"
              disabled={busy}
              onPress={() =>
                Alert.alert(
                  "Lock board?",
                  "No further claims or releases will be allowed. Random numbers will be drawn.",
                  [
                    { text: "Cancel", style: "cancel" },
                    {
                      text: "Lock board",
                      onPress: () => mutate(`/squares/${id}/lock`, "POST"),
                    },
                  ],
                )
              }
            />
          )}
          <Text style={ui.heading}>Results & payouts</Text>
          {!d.payouts.length && (
            <Text style={ui.copy}>
              Results appear after scoring checkpoints are settled.
            </Text>
          )}
          {d.payouts.map((p) => (
            <Card key={`${p.game_id}-${p.checkpoint}`}>
              <Text style={ui.heading}>
                {p.checkpoint.toUpperCase()} · {p.away_score}–{p.home_score}
              </Text>
              <Text style={ui.text}>
                {p.winner_display_name || "Unclaimed square"}
                {p.amount_cents != null
                  ? ` · $${(p.amount_cents / 100).toFixed(2)}`
                  : ""}
              </Text>
            </Card>
          ))}
        </>
      )}
    </Screen>
  );
}
