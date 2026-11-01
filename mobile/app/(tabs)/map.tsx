import { useEffect, useMemo, useRef, useState } from "react";
import { FlatList, Pressable, Text, View } from "react-native";
import MapView, { Circle, Polygon, type Region } from "react-native-maps";
import { Card, Input, Muted, Pill, Screen, colors } from "@/components/ui";
import { api } from "@/lib/api";
import { useLocation } from "@/lib/location";
import { useMyStatus } from "@/lib/useStatus";

interface Zone {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  zone_type: string;
  risk_level: string | null;
  description: string | null;
  geometry: { type: string; coordinates: number[][][] | number[][][][] } | null;
  synthetic: boolean;
}

const ZONE_COLOR: Record<string, string> = { RESTRICTED: "#dc2626", HIGH_RISK: "#ea580c", CAUTION: "#d97706", SAFE: "#15803d" };
const FILTERS = ["ALL", "RESTRICTED", "HIGH_RISK", "CAUTION", "SAFE"];

function colorFor(z: Zone) {
  return z.synthetic ? "#7c3aed" : ZONE_COLOR[z.zone_type] ?? "#0284c7";
}

function rings(z: Zone): { latitude: number; longitude: number }[][] {
  if (!z.geometry) return [];
  const polys = (z.geometry.type === "Polygon" ? [z.geometry.coordinates] : z.geometry.coordinates) as number[][][][];
  return polys.map((r) => r[0].map(([lon, lat]) => ({ latitude: lat, longitude: lon })));
}

export default function SafetyMap() {
  const { lastFix } = useLocation();
  const { status } = useMyStatus(30000);
  const [zones, setZones] = useState<Zone[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("ALL");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Zone | null>(null);
  const map = useRef<MapView>(null);

  useEffect(() => {
    api<Zone[]>("/api/v1/zones?active=true").then(setZones).catch((e) => setError(e instanceof Error ? e.message : "Could not load zones"));
  }, []);

  const visible = useMemo(
    () => zones.filter((z) => (filter === "ALL" || z.zone_type === filter) && (!query || z.name.toLowerCase().includes(query.toLowerCase()))),
    [zones, filter, query],
  );

  const here = lastFix ?? (status?.location.latitude != null ? { latitude: status.location.latitude!, longitude: status.location.longitude! } : null);
  const initial: Region = {
    latitude: here?.latitude ?? zones[0]?.latitude ?? 12.9716,
    longitude: here?.longitude ?? zones[0]?.longitude ?? 77.5946,
    latitudeDelta: 0.05,
    longitudeDelta: 0.05,
  };

  function focus(z: Zone) {
    setSelected(z);
    map.current?.animateToRegion({ latitude: z.latitude, longitude: z.longitude, latitudeDelta: 0.01, longitudeDelta: 0.01 }, 500);
  }

  return (
    <Screen>
      <View style={{ padding: 12, gap: 8, backgroundColor: colors.panel, borderBottomWidth: 1, borderColor: colors.line }}>
        <Input value={query} onChangeText={setQuery} placeholder="Search zones" style={{ minHeight: 42 }} />
        <FlatList
          horizontal
          data={FILTERS}
          keyExtractor={(f) => f}
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ gap: 6 }}
          renderItem={({ item }) => (
            <Pressable onPress={() => setFilter(item)} style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: 6, backgroundColor: filter === item ? colors.brand : "#eef2f4" }}>
              <Text style={{ color: filter === item ? "#fff" : colors.text, fontWeight: "600", fontSize: 13 }}>{item === "ALL" ? "All" : item.replace("_", " ").toLowerCase()}</Text>
            </Pressable>
          )}
        />
      </View>
      <View style={{ flex: 1 }}>
        <MapView ref={map} style={{ flex: 1 }} initialRegion={initial} showsUserLocation showsMyLocationButton onPress={() => setSelected(null)}>
          {visible.map((z) =>
            z.geometry ? (
              rings(z).map((coords, i) => (
                <Polygon key={`p${z.id}-${i}`} coordinates={coords} strokeColor={colorFor(z)} fillColor={`${colorFor(z)}33`} strokeWidth={2} tappable onPress={() => setSelected(z)} />
              ))
            ) : (
              <Circle key={`c${z.id}`} center={{ latitude: z.latitude, longitude: z.longitude }} radius={z.radius_meters} strokeColor={colorFor(z)} fillColor={`${colorFor(z)}33`} strokeWidth={2} />
            ),
          )}
        </MapView>
        <View style={{ position: "absolute", top: 10, left: 10, backgroundColor: "#ffffffee", borderRadius: 8, padding: 8, gap: 4 }}>
          {[["Restricted", "#dc2626"], ["High risk", "#ea580c"], ["Caution", "#d97706"], ["Safe area", "#15803d"], ["Test data", "#7c3aed"]].map(([l, c]) => (
            <View key={l} style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
              <View style={{ width: 10, height: 10, borderRadius: 5, borderWidth: 2, borderColor: c }} />
              <Text style={{ fontSize: 11, color: colors.text }}>{l}</Text>
            </View>
          ))}
        </View>
      </View>
      <View style={{ padding: 12, gap: 8 }}>
        {error && <Text style={{ color: colors.sos }}>{error}</Text>}
        {selected ? (
          <Card>
            <Text style={{ fontWeight: "700", fontSize: 16, color: colors.text }}>{selected.name}</Text>
            <View style={{ flexDirection: "row", gap: 6, marginTop: 6 }}>
              <Pill text={selected.zone_type.replace("_", " ")} color="#fff" background={colorFor(selected)} />
              <Pill text={`${Math.round(selected.radius_meters)} m`} />
              {selected.synthetic && <Pill text="Synthetic test data" color="#5b21b6" background="#ede9fe" />}
            </View>
            {selected.description && <Muted style={{ marginTop: 6 }}>{selected.description.slice(0, 200)}</Muted>}
          </Card>
        ) : (
          <Card>
            <Text style={{ fontWeight: "600", color: colors.text }}>
              {status?.zones?.nearest_restricted
                ? `Nearest restricted zone: ${status.zones.nearest_restricted.zone_name} (${Math.round(status.zones.nearest_restricted.distance_meters)} m)`
                : here
                  ? "No active restricted zones near you"
                  : "Waiting for your location"}
            </Text>
            <Muted>{visible.length} zones shown · tap a zone name below to focus</Muted>
            <FlatList
              horizontal
              style={{ marginTop: 8 }}
              data={visible.slice(0, 30)}
              keyExtractor={(z) => String(z.id)}
              contentContainerStyle={{ gap: 6 }}
              renderItem={({ item }) => (
                <Pressable onPress={() => focus(item)} style={{ borderWidth: 1, borderColor: colors.line, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6 }}>
                  <Text style={{ fontSize: 13, color: colors.text }}>{item.name}</Text>
                </Pressable>
              )}
            />
          </Card>
        )}
      </View>
    </Screen>
  );
}
