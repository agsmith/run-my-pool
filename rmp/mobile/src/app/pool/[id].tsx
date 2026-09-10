import {
  Redirect,
  useFocusEffect,
  useLocalSearchParams,
  router,
} from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";
import { apiFetch } from "@/api/client";
import type { Pool } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { Screen } from "@/components/Screen";
import { PoolBreakdown } from "@/components/PoolBreakdown";
import type { Breakdown } from "@/domain/survivor";
import { colors } from "@/theme";
export default function PoolScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status } = useAuth();
  const [pool, setPool] = useState<Pool | null>(null);
  const [week, setWeek] = useState<number | null>(null);
  const [rows, setRows] = useState<Breakdown[] | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useFocusEffect(
    useCallback(() => {
      let active = true;
      async function load() {
        if (status !== "authenticated" || !id) return;
        try {
          const value = await apiFetch<Pool>(`/pools/${id}`);
          if (!active) return;
          setPool(value);
          if (value.pool_type === "survivor") {
            const summary = await apiFetch<{ week: number }>(
              `/pools/${id}/activity-summary`,
            );
            const breakdown = await apiFetch<Breakdown[]>(
              `/picks/pool/${id}/week/${summary.week}/breakdown`,
            );
            if (active) {
              setWeek(summary.week);
              setRows(breakdown);
            }
          }
          if (active) setError("");
        } catch (e) {
          if (active) {
            setRows(null);
            setError(e instanceof Error ? e.message : "Unable to load pool");
          }
        }
      }
      load();
      const timer = setInterval(load, 30000);
      return () => {
        active = false;
        clearInterval(timer);
      };
    }, [id, status, refresh]),
  );
  if (status === "anonymous") return <Redirect href="/login" />;
  return (
    <Screen>
      {pool ? (
        <>
          <Text style={s.kicker}>{pool.pool_type.toUpperCase()}</Text>
          <Text style={s.title}>{pool.name}</Text>
          <Text style={s.copy}>
            {week ? `Week ${week} · Pool Home` : "Pool Home"}
          </Text>
          <Pressable
            accessibilityRole="button"
            style={s.primary}
            onPress={() =>
              pool.pool_type === "survivor"
                ? router.push({ pathname: "/survivor/[id]", params: { id } })
                : router.push({
                    pathname: "/web",
                    params: {
                      path: `/pool/${id}/${pool.pool_type === "pickem" ? "pickem" : "squares"}`,
                    },
                  })
            }
          >
            <Text style={s.primaryText}>
              {pool.pool_type === "survivor"
                ? "My entries & picks"
                : "Open picks on website"}
            </Text>
          </Pressable>
          {rows && <PoolBreakdown rows={rows} />}
          <Pressable
            accessibilityRole="button"
            style={s.secondary}
            onPress={() =>
              router.push({
                pathname: "/web",
                params: { path: `/pool/${id}/leaderboard` },
              })
            }
          >
            <Text style={s.secondaryText}>Leaderboard on website</Text>
          </Pressable>
        </>
      ) : (
        !error && <ActivityIndicator color={colors.lime} />
      )}{" "}
      {!!error && (
        <Text accessibilityRole="alert" style={s.error}>
          {error}
        </Text>
      )}
      <Pressable
        accessibilityRole="button"
        style={s.secondary}
        onPress={() => setRefresh((v) => v + 1)}
      >
        <Text style={s.secondaryText}>Refresh pool</Text>
      </Pressable>
    </Screen>
  );
}
const s = StyleSheet.create({
  kicker: { color: colors.lime, fontWeight: "900", letterSpacing: 2 },
  title: { color: colors.text, fontSize: 34, fontWeight: "900" },
  copy: { color: colors.muted, fontSize: 16, lineHeight: 23 },
  primary: {
    backgroundColor: colors.lime,
    padding: 16,
    minHeight: 50,
    borderRadius: 12,
    alignItems: "center",
  },
  primaryText: { color: colors.ink, fontWeight: "900", fontSize: 16 },
  secondary: {
    borderColor: colors.line,
    borderWidth: 1,
    padding: 16,
    minHeight: 48,
    borderRadius: 12,
    alignItems: "center",
  },
  secondaryText: { color: colors.cyan, fontWeight: "800", fontSize: 16 },
  error: { color: colors.danger },
});
