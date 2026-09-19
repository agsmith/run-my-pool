import { TeamHelmet } from "@/components/TeamHelmet";
import { apiTime } from "@/domain/time";
import { Stack, useLocalSearchParams } from "expo-router";
import { useCallback } from "react";
import { ScrollView, Text, View } from "react-native";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import type { Game } from "@/domain/survivor";
import { Screen } from "@/components/Screen";
import { Card, LoadState, ui } from "@/components/NativeUI";
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
  payouts: {
    game_id: number;
    checkpoint: string;
    winner_display_name: string | null;
    home_score: number;
    away_score: number;
  }[];
};
export default function Squares() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const r = useResource(
    useCallback(() => apiFetch<Board>(`/squares/${id}`), [id]),
  );
  const d = r.data;
  const locked = !!d && (d.locked || apiTime(d.lock_time) <= Date.now());
  return (
    <Screen refreshing={r.busy} onRefresh={r.reload}>
      <Stack.Screen options={{ title: "Squares" }} />
      <Text style={ui.title}>Squares</Text>
      <LoadState busy={r.busy} error={r.error} empty={!d} />
      {d && (
        <>
          <Text style={ui.heading}>{d.pool_name}</Text>
          {d.games.map((g) => (
            <View key={g.game_id} style={{ gap: 8 }}>
              <View style={ui.row}>
                <TeamHelmet team={g.away_team.abbrv} />
                <Text style={ui.copy}>at</Text>
                <TeamHelmet team={g.home_team.abbrv} />
              </View>
              <Text style={ui.copy}>
                {g.away_team.name} at {g.home_team.name} ·{" "}
                {new Date(apiTime(g.start_time)).toLocaleString()}
              </Text>
            </View>
          ))}
          <Text style={ui.copy}>
            {d.claims.length}/100 claimed · {locked ? "Locked" : "Open"}
          </Text>
          <Text style={ui.copy}>
            Swipe the board sideways to see all columns. Numbers appear when
            the board locks. This board is read-only in the app.
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
                      <View
                        accessibilityLabel={`Square ${number}, ${owned?.display_name || "available"}`}
                        key={column}
                        style={{
                          width: 52,
                          height: 52,
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 6,
                          backgroundColor: owned
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
                            color: colors.text,
                            fontWeight: "800",
                          }}
                        >
                          {number}
                        </Text>
                        <Text
                          numberOfLines={1}
                          style={{
                            color: colors.muted,
                            fontSize: 10,
                            paddingHorizontal: 2,
                          }}
                        >
                          {owned?.display_name || "Open"}
                        </Text>
                      </View>
                    );
                  })}
                </View>
              ))}
            </View>
          </ScrollView>
          <Text style={ui.heading}>Results</Text>
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
              </Text>
            </Card>
          ))}
        </>
      )}
    </Screen>
  );
}
