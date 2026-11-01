import { useEffect, useState } from "react";
import { FlatList, Pressable, Text, View } from "react-native";
import { Muted, Pill, Screen, colors } from "@/components/ui";
import { api } from "@/lib/api";
import type { Trip } from "@/lib/useStatus";

interface Point {
  latitude: number;
  longitude: number;
  accuracy: number | null;
  safety_status: string | null;
  recorded_at: string;
}

export default function History() {
  const [tab, setTab] = useState<"trips" | "points">("trips");
  const [trips, setTrips] = useState<Trip[]>([]);
  const [points, setPoints] = useState<Point[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Trip[]>("/api/v1/me/trips").then(setTrips).catch((e) => setError(e.message));
    api<Point[]>("/api/v1/me/locations?hours=72").then(setPoints).catch((e) => setError(e.message));
  }, []);

  return (
    <Screen>
      <View style={{ flexDirection: "row", gap: 8, padding: 16, paddingBottom: 0 }}>
        {(["trips", "points"] as const).map((t) => (
          <Pressable key={t} onPress={() => setTab(t)} style={{ flex: 1, padding: 10, borderRadius: 8, backgroundColor: tab === t ? colors.brand : colors.panel, borderWidth: 1, borderColor: colors.line }}>
            <Text style={{ textAlign: "center", fontWeight: "600", color: tab === t ? "#fff" : colors.text }}>{t === "trips" ? "Trips" : "Locations (72 h)"}</Text>
          </Pressable>
        ))}
      </View>
      {error && <Text style={{ color: colors.sos, padding: 16 }}>{error}</Text>}
      {tab === "trips" ? (
        <FlatList
          data={trips}
          keyExtractor={(t) => String(t.id)}
          contentContainerStyle={{ padding: 16, gap: 8 }}
          ListEmptyComponent={<Muted>No trips yet.</Muted>}
          renderItem={({ item }) => (
            <View style={{ backgroundColor: colors.panel, borderRadius: 10, borderWidth: 1, borderColor: colors.line, padding: 14 }}>
              <Text style={{ fontWeight: "700", color: colors.text }}>{item.title}</Text>
              <Muted>{item.destination ?? "No destination"}</Muted>
              <Muted>{new Date(item.started_at).toLocaleString()} → {item.ended_at ? new Date(item.ended_at).toLocaleString() : "ongoing"}</Muted>
              <View style={{ marginTop: 6 }}><Pill text={item.status.toLowerCase()} /></View>
            </View>
          )}
        />
      ) : (
        <FlatList
          data={points}
          keyExtractor={(p, i) => `${p.recorded_at}-${i}`}
          contentContainerStyle={{ padding: 16, gap: 6 }}
          ListEmptyComponent={<Muted>No locations recorded in the last 72 hours.</Muted>}
          renderItem={({ item }) => (
            <View style={{ flexDirection: "row", justifyContent: "space-between", backgroundColor: colors.panel, padding: 12, borderRadius: 8 }}>
              <Text style={{ color: colors.text, fontVariant: ["tabular-nums"] }}>{item.latitude.toFixed(5)}, {item.longitude.toFixed(5)}</Text>
              <Muted>{new Date(item.recorded_at).toLocaleTimeString()}</Muted>
            </View>
          )}
        />
      )}
    </Screen>
  );
}
