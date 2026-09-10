import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { Breakdown } from "@/domain/survivor";
import { colors } from "@/theme";
export function PoolBreakdown({ rows }: { rows: Breakdown[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const count = rows.reduce((sum, row) => sum + row.count, 0);
  return (
    <View style={s.panel}>
      <Text style={s.title}>Who picked whom</Text>
      <Text style={s.copy}>
        Both teams’ picks lock and appear at kickoff. Remaining picks appear at
        the pool deadline.
      </Text>
      <Text style={s.copy}>
        {count
          ? `${count} active entries with revealed picks`
          : "No active entries have revealed picks yet."}
      </Text>
      {rows.map((row) => (
        <View key={row.team} style={s.team}>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ expanded: expanded === row.team }}
            onPress={() => setExpanded(expanded === row.team ? null : row.team)}
            style={s.row}
          >
            <Text style={s.name}>{row.team_name}</Text>
            <Text style={s.count}>
              {row.count} · {expanded === row.team ? "−" : "+"}
            </Text>
          </Pressable>
          {expanded === row.team &&
            row.entries?.map((entry) => (
              <Text style={s.entry} key={entry.entry_id}>
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
  team: { borderTopWidth: 1, borderColor: colors.line },
  row: { flexDirection: "row", alignItems: "center", gap: 12, minHeight: 52 },
  name: { flex: 1, color: colors.text, fontSize: 16, fontWeight: "700" },
  count: { color: colors.lime, fontWeight: "800" },
  entry: { color: colors.muted, paddingVertical: 8, fontSize: 16 },
});
