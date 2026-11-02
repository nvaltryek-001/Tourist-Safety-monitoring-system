import { router } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Animated, FlatList, Linking, Platform, Pressable, Text, View } from "react-native";
import MapView, { Circle, Marker, Polygon, Polyline, PROVIDER_DEFAULT, PROVIDER_GOOGLE, type Region } from "react-native-maps";
import { Button, Card, Input, Muted, Pill, Screen, colors } from "@/components/ui";
import { api } from "@/lib/api";
import { useLocation } from "@/lib/location";
import { FACILITY_COLOR, FACILITY_LABEL, type Facility, useNearbyHelp } from "@/lib/nearby";
import { formatDistance, navigationUrl } from "@/lib/url";
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
// Google Maps on Android (Expo Go ships a key; standalone builds use GOOGLE_MAPS_ANDROID_API_KEY).
const PROVIDER = Platform.OS === "android" ? PROVIDER_GOOGLE : PROVIDER_DEFAULT;

function colorFor(z: Zone) {
  return z.synthetic ? "#7c3aed" : ZONE_COLOR[z.zone_type] ?? "#0284c7";
}

function rings(z: Zone): { latitude: number; longitude: number }[][] {
  if (!z.geometry) return [];
  const polys = (z.geometry.type === "Polygon" ? [z.geometry.coordinates] : z.geometry.coordinates) as number[][][][];
  return polys.map((r) => r[0].map(([lon, lat]) => ({ latitude: lat, longitude: lon })));
}

type Selected = { kind: "zone"; zone: Zone } | { kind: "facility"; facility: Facility } | null;

export default function SafetyMap() {
  const { lastFix } = useLocation();
  const { status } = useMyStatus(30000);
  const [zones, setZones] = useState<Zone[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("ALL");
  const [query, setQuery] = useState("");
  const [showHelp, setShowHelp] = useState(true);
  const [selected, setSelected] = useState<Selected>(null);
  const map = useRef<MapView>(null);
  const slide = useRef(new Animated.Value(0)).current;

  const here = lastFix ?? (status?.location.latitude != null ? { latitude: status.location.latitude!, longitude: status.location.longitude! } : null);
  // Round so the nearby query is not repeated for every small GPS movement.
  const help = useNearbyHelp(here ? Number(here.latitude.toFixed(3)) : null, here ? Number(here.longitude.toFixed(3)) : null);

  useEffect(() => {
    api<Zone[]>("/api/v1/zones?active=true").then(setZones).catch((e) => setError(e instanceof Error ? e.message : "Could not load zones"));
  }, []);

  useEffect(() => {
    Animated.spring(slide, { toValue: selected ? 1 : 0, useNativeDriver: true, friction: 8 }).start();
  }, [selected, slide]);

  const visible = useMemo(
    () => zones.filter((z) => (filter === "ALL" || z.zone_type === filter) && (!query || z.name.toLowerCase().includes(query.toLowerCase()))),
    [zones, filter, query],
  );
  const facilities = showHelp ? help.data?.nearby ?? [] : [];

  const initial: Region = {
    latitude: here?.latitude ?? zones[0]?.latitude ?? 12.9716,
    longitude: here?.longitude ?? zones[0]?.longitude ?? 77.5946,
    latitudeDelta: 0.04,
    longitudeDelta: 0.04,
  };

  function focus(lat: number, lon: number, delta = 0.01) {
    map.current?.animateToRegion({ latitude: lat, longitude: lon, latitudeDelta: delta, longitudeDelta: delta }, 500);
  }

  const routeTo = selected?.kind === "facility" ? selected.facility : null;

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
          ListFooterComponent={
            <Pressable onPress={() => setShowHelp((v) => !v)} style={{ marginLeft: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 6, backgroundColor: showHelp ? "#1d4ed8" : "#eef2f4" }}>
              <Text style={{ color: showHelp ? "#fff" : colors.text, fontWeight: "600", fontSize: 13 }}>Police & hospitals</Text>
            </Pressable>
          }
          renderItem={({ item }) => (
            <Pressable onPress={() => setFilter(item)} style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: 6, backgroundColor: filter === item ? colors.brand : "#eef2f4" }}>
              <Text style={{ color: filter === item ? "#fff" : colors.text, fontWeight: "600", fontSize: 13 }}>{item === "ALL" ? "All zones" : item.replace("_", " ").toLowerCase()}</Text>
            </Pressable>
          )}
        />
      </View>

      <View style={{ flex: 1 }}>
        <MapView
          ref={map}
          provider={PROVIDER}
          style={{ flex: 1 }}
          initialRegion={initial}
          showsUserLocation
          showsMyLocationButton
          showsCompass
          toolbarEnabled={false}
          onPress={() => setSelected(null)}
        >
          {visible.map((z) =>
            z.geometry ? (
              rings(z).map((coords, i) => (
                <Polygon key={`p${z.id}-${i}`} coordinates={coords} strokeColor={colorFor(z)} fillColor={`${colorFor(z)}33`} strokeWidth={2}
                  tappable onPress={() => setSelected({ kind: "zone", zone: z })} />
              ))
            ) : (
              <Circle key={`c${z.id}`} center={{ latitude: z.latitude, longitude: z.longitude }} radius={z.radius_meters}
                strokeColor={colorFor(z)} fillColor={`${colorFor(z)}33`} strokeWidth={2} />
            ),
          )}
          {visible.filter((z) => !z.geometry).map((z) => (
            <Marker key={`zc${z.id}`} coordinate={{ latitude: z.latitude, longitude: z.longitude }} anchor={{ x: 0.5, y: 0.5 }}
              onPress={() => setSelected({ kind: "zone", zone: z })} tracksViewChanges={false}>
              <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colorFor(z), borderWidth: 2, borderColor: "#fff" }} />
            </Marker>
          ))}
          {facilities.map((f) => (
            <Marker key={`f${f.id}`} coordinate={{ latitude: f.latitude, longitude: f.longitude }} pinColor={FACILITY_COLOR[f.facility_type]}
              title={f.name} description={`${FACILITY_LABEL[f.facility_type]} · ${formatDistance(f.distance_meters)}`}
              onPress={() => setSelected({ kind: "facility", facility: f })} />
          ))}
          {routeTo && here && (
            <Polyline coordinates={[{ latitude: here.latitude, longitude: here.longitude }, { latitude: routeTo.latitude, longitude: routeTo.longitude }]}
              strokeColor="#dc2626" strokeWidth={4} lineDashPattern={[12, 8]} />
          )}
        </MapView>

        <View style={{ position: "absolute", top: 10, left: 10, backgroundColor: "#ffffffee", borderRadius: 8, padding: 8, gap: 4 }}>
          {[["Restricted", "#dc2626"], ["High risk", "#ea580c"], ["Caution", "#d97706"], ["Safe area", "#15803d"], ["Test data", "#7c3aed"], ["Police", "#1d4ed8"], ["Hospital", "#be123c"]].map(([l, c]) => (
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
          <Animated.View style={{ transform: [{ translateY: slide.interpolate({ inputRange: [0, 1], outputRange: [30, 0] }) }], opacity: slide }}>
            {selected.kind === "zone" ? (
              <Card>
                <Text style={{ fontWeight: "700", fontSize: 16, color: colors.text }}>{selected.zone.name}</Text>
                <View style={{ flexDirection: "row", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                  <Pill text={selected.zone.zone_type.replace("_", " ")} color="#fff" background={colorFor(selected.zone)} />
                  <Pill text={`${Math.round(selected.zone.radius_meters)} m`} />
                  {selected.zone.synthetic && <Pill text="Synthetic test data" color="#5b21b6" background="#ede9fe" />}
                </View>
                {selected.zone.description && <Muted style={{ marginTop: 6 }}>{selected.zone.description.slice(0, 200)}</Muted>}
              </Card>
            ) : (
              <Card style={{ gap: 6 }}>
                <Text style={{ fontWeight: "700", fontSize: 16, color: colors.text }}>{selected.facility.name}</Text>
                <Muted>{FACILITY_LABEL[selected.facility.facility_type]} · {formatDistance(selected.facility.distance_meters)} straight line</Muted>
                <View style={{ flexDirection: "row", gap: 8 }}>
                  <Button title="Navigate" onPress={() => Linking.openURL(navigationUrl(selected.facility.latitude, selected.facility.longitude))} style={{ flex: 1 }} />
                  {selected.facility.phone && (
                    <Button title="Call" variant="secondary" onPress={() => Linking.openURL(`tel:${selected.facility.phone}`)} style={{ flex: 1 }} />
                  )}
                </View>
              </Card>
            )}
          </Animated.View>
        ) : (
          <Card>
            <Text style={{ fontWeight: "600", color: colors.text }}>
              {status?.zones?.nearest_restricted
                ? `Nearest restricted zone: ${status.zones.nearest_restricted.zone_name} (${Math.round(status.zones.nearest_restricted.distance_meters)} m)`
                : here ? "No active restricted zones near you" : "Waiting for your location"}
            </Text>
            {help.data?.police && (
              <Pressable onPress={() => { setSelected({ kind: "facility", facility: help.data!.police! }); focus(help.data!.police!.latitude, help.data!.police!.longitude, 0.03); }}>
                <Muted style={{ marginTop: 4 }}>🚓 Nearest police: {help.data.police.name} · {formatDistance(help.data.police.distance_meters)}</Muted>
              </Pressable>
            )}
            {help.data?.hospital && (
              <Pressable onPress={() => { setSelected({ kind: "facility", facility: help.data!.hospital! }); focus(help.data!.hospital!.latitude, help.data!.hospital!.longitude, 0.03); }}>
                <Muted>🏥 Nearest hospital: {help.data.hospital.name} · {formatDistance(help.data.hospital.distance_meters)}</Muted>
              </Pressable>
            )}
            <View style={{ flexDirection: "row", gap: 8, marginTop: 8 }}>
              <Button title="All nearby help" variant="secondary" onPress={() => router.push("/help")} style={{ flex: 1, minHeight: 42 }} />
              {here && <Button title="Center on me" variant="secondary" onPress={() => focus(here.latitude, here.longitude)} style={{ flex: 1, minHeight: 42 }} />}
            </View>
          </Card>
        )}
      </View>
    </Screen>
  );
}
