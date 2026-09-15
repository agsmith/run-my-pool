import { TeamHelmet } from "./TeamHelmet";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { Breakdown, PickEmWeeklyStanding } from "@/domain/survivor";
import { colors } from "@/theme";
export function PoolBreakdown({ rows, poolType = "survivor", standings = [] }: { rows: Breakdown[]; poolType?: "survivor" | "pickem"; standings?: PickEmWeeklyStanding[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const count = rows.reduce((sum, row) => sum + row.count, 0);
  if (poolType === "pickem") {
    const teamsByEntry = new Map<string, { team: string; result?: string | null }[]>();
    rows.forEach((row) => row.entries?.forEach((entry) => {
      const picks = teamsByEntry.get(entry.entry_id) || [];
      picks.push({ team: row.team_abbrv || row.team, result: row.result });
      teamsByEntry.set(entry.entry_id, picks);
    }));
    return (
      <View style={s.panel}>
        <Text style={s.title}>Pick Breakdown</Text>
        <Text style={s.copy}>Week standings after the weekly lock.</Text>
        {standings.length === 0 ? <Text style={s.copy}>No entries have revealed picks yet.</Text> : standings.map((row) => (
          <View key={row.entry_id} style={s.standingRow}>
            <View style={s.standingHeader}>
              <Text style={s.rank}>#{row.rank}</Text>
              <View style={s.member}><Text style={s.memberName}>{row.user_display_name}</Text><Text style={s.entry}>{row.entry_name}</Text></View>
              <Text style={s.wins}>{row.points} {row.points === 1 ? "win" : "wins"}</Text>
            </View>
            <View style={s.pickLabels}>
              {(teamsByEntry.get(row.entry_id) || []).map((pick, index) => <Text key={`${pick.team}-${index}`} style={[s.pickLabel, pick.result === "win" ? s.winLabel : pick.result === "loss" ? s.lossLabel : null]}>{pick.team} · {pick.result === "win" ? "W" : pick.result === "loss" ? "L" : "—"}</Text>)}
              {row.predicted_total != null && <Text style={s.tiebreak}>Total: {row.predicted_total}</Text>}
            </View>
          </View>
        ))}
      </View>
    );
  }
  return (
    <View style={s.panel}>
      <Text style={s.title}>Pick Breakdown</Text>
      <Text style={s.copy}>
        Both teams’ picks lock and appear at kickoff. Remaining picks appear at
        the pool deadline.
      </Text>
      <Text style={s.copy}>
        {count
          ? `${count} ${count === 1 ? "entry" : "entries"} with revealed picks`
          : "No entries have revealed picks yet."}
      </Text>
      {rows.map((row) => (
        <View key={row.team} style={[s.team, row.result === "win" ? s.winBorder : row.result === "loss" ? s.lossBorder : null]}>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ expanded: expanded === row.team }}
            onPress={() => setExpanded(expanded === row.team ? null : row.team)}
            style={s.row}
          >
            <TeamHelmet team={row.team} size={52} />
            <Text style={s.name}>{row.team_name}{row.result === "win" ? " · Win" : row.result === "loss" ? " · Loss" : ""}</Text>
            <Text style={[s.count, row.result === "win" ? s.winText : row.result === "loss" ? s.lossText : null]}>
              {row.count} · {expanded === row.team ? "−" : "+"}
            </Text>
          </Pressable>
          {expanded === row.team &&
            row.entries?.map((entry) => (
              <Text style={s.survivorEntry} key={entry.entry_id}>
                {entry.entry_name}
              </Text>
            ))}
        </View>
      ))}
    </View>
  );
}
const s = StyleSheet.create({
  panel: {
    gap: 12,
    padding: 16,
    backgroundColor: colors.panel,
    borderRadius: 16,
  },
  title: { color: colors.text, fontSize: 23, fontWeight: "800" },
  copy: { color: colors.muted, lineHeight: 22 },
  team: { borderWidth: 1, borderColor: colors.line, padding: 8, borderRadius: 8 },
  winBorder: { borderColor: "#62c98b" },
  lossBorder: { borderColor: "#f19aaf" },
  winText: { color: "#62c98b" },
  lossText: { color: "#f19aaf" },
  row: { flexDirection: "row", alignItems: "center", gap: 12, minHeight: 52 },
  name: { flex: 1, color: colors.text, fontSize: 16, fontWeight: "700" },
  count: { color: colors.muted, fontWeight: "800" },
  survivorEntry: { color: colors.muted, paddingVertical: 8, fontSize: 16 },
  standingRow: { borderTopWidth: 1, borderTopColor: colors.line, paddingVertical: 12, gap: 8 },
  standingHeader: { flexDirection: "row", alignItems: "center", gap: 10 },
  rank: { color: colors.cyan, fontWeight: "800", width: 28 },
  member: { flex: 1 },
  memberName: { color: colors.text, fontSize: 16, fontWeight: "800" },
  entry: { color: colors.muted, fontSize: 13 },
  wins: { color: colors.lime, fontWeight: "800" },
  pickLabels: { flexDirection: "row", flexWrap: "wrap", gap: 6, paddingLeft: 38 },
  pickLabel: { color: colors.muted, borderWidth: 1, borderColor: colors.line, borderRadius: 6, paddingHorizontal: 7, paddingVertical: 4, fontSize: 12, fontWeight: "700" },
  winLabel: { color: "#b9f6cf", borderColor: "#62c98b" },
  lossLabel: { color: "#ffd0dd", borderColor: "#f19aaf" },
  tiebreak: { color: colors.cyan, fontSize: 12, fontWeight: "800", paddingVertical: 4 },
});
