import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Linking, Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { Button, Card, Label, Muted, Pill, Row, Screen, colors, timeAgo } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLocation } from "@/lib/location";
import { accuracyLabel, sosStatusText, statusView } from "@/lib/status";
import { useMyStatus } from "@/lib/useStatus";

export default function Home() {
  const { profile } = useAuth();
  const loc = useLocation();
  const { status, error, reload } = useMyStatus();
  const view = statusView(status?.display_state);
  const consent = !!profile?.location_consent_at;
  const [weather, setWeather] = useState<{ available: boolean; weather_risk_level?: string; reasons?: string[]; current?: { temperature_2m?: number; precipitation?: number } } | null>(null);
  const wlat = loc.lastFix ? loc.lastFix.latitude.toFixed(2) : null;
  const wlon = loc.lastFix ? loc.lastFix.longitude.toFixed(2) : null;
  useEffect(() => {
    if (!wlat || !wlon) return;
    api<typeof weather>(`/api/v1/weather?lat=${wlat}&lon=${wlon}`).then(setWeather).catch(() => setWeather(null));
  }, [wlat, wlon]);

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} refreshControl={<RefreshControl refreshing={false} onRefresh={reload} />}>
        <View>
          <Muted>Hello,</Muted>
          <Text style={{ fontSize: 24, fontWeight: "700", color: colors.text }}>{profile?.name ?? "Tourist"}</Text>
        </View>

        <View style={{ backgroundColor: view.background, borderRadius: 12, padding: 18 }} accessibilityRole="summary">
          <Text style={{ color: view.color, fontSize: 12, fontWeight: "700", letterSpacing: 1 }}>CURRENT SAFETY STATUS</Text>
          <Text style={{ color: view.color, fontSize: 26, fontWeight: "700", marginTop: 6 }}>{status ? view.label : "Checking…"}</Text>
          <Text style={{ color: view.color, marginTop: 6, lineHeight: 20 }}>{status ? view.message : "Contacting the safety server."}</Text>
          {status?.zones?.inside.map((z) => (
            <Text key={z.zone_id} style={{ color: view.color, marginTop: 8, fontWeight: "600" }}>• Inside {z.zone_name}</Text>
          ))}
          {status?.zones?.nearest_restricted && !status.zones.inside.length && (
            <Text style={{ color: view.color, marginTop: 8 }}>
              Nearest restricted zone: {status.zones.nearest_restricted.zone_name} · {Math.round(status.zones.nearest_restricted.distance_meters)} m
            </Text>
          )}
        </View>
        {error && <Text style={{ color: colors.sos }}>{error}</Text>}

        {status?.active_sos && (
          <Pressable onPress={() => router.push(`/sos-status/${status.active_sos!.id}`)}>
            <Card style={{ borderColor: "#fca5a5", backgroundColor: "#fff1f2" }}>
              <Label>Active emergency · SOS #{status.active_sos.id}</Label>
              <Text style={{ fontWeight: "600", color: colors.sosDark }}>{sosStatusText(status.active_sos.status)}</Text>
              <Muted style={{ marginTop: 4 }}>Tap to track the response</Muted>
            </Card>
          </Pressable>
        )}

        <Card>
          <Label>Location sharing</Label>
          {!consent ? (
            <>
              <Muted>Location sharing is off. Your safety cannot be assessed without it.</Muted>
              <Button title="Review & enable" onPress={() => router.push("/consent")} style={{ marginTop: 12 }} />
            </>
          ) : loc.permission === "denied" || loc.permission === "services_off" ? (
            <>
              <Muted>
                {loc.permission === "services_off" ? "Location services are turned off on this phone." : "Location permission was denied. Enable it in system settings."}
              </Muted>
              <Button title="Open settings" variant="secondary" onPress={() => Linking.openSettings()} style={{ marginTop: 12 }} />
            </>
          ) : (
            <>
              <Row label="GPS" value={<Pill text={loc.sharing ? "Sharing" : "Starting…"} color={loc.sharing ? colors.safe : colors.muted} background={loc.sharing ? "#dcfce7" : "#eef2f4"} />} />
              <Row label="Accuracy" value={accuracyLabel(loc.lastFix?.accuracy)} />
              <Row label="Current position" value={loc.lastFix ? `${loc.lastFix.latitude.toFixed(5)}, ${loc.lastFix.longitude.toFixed(5)}` : "Waiting for GPS fix"} />
              <Row label="Last sent to server" value={timeAgo(loc.lastSyncAt ?? status?.last_location_update ?? null)} />
              {loc.pending > 0 && <Row label="Waiting to upload" value={`${loc.pending} point(s)`} />}
              {loc.syncError && <Text style={{ color: colors.warn, marginTop: 6 }}>{loc.syncError} — will retry automatically.</Text>}
              {!loc.sharing && loc.permission !== "granted" && <Button title="Allow location" onPress={() => void loc.start()} style={{ marginTop: 12 }} />}
            </>
          )}
        </Card>

        {weather?.available && (
          <Card style={{ borderColor: weather.weather_risk_level === "HIGH" ? "#fca5a5" : weather.weather_risk_level === "MEDIUM" ? "#fcd34d" : colors.line }}>
            <Label>Weather here</Label>
            <Text style={{ color: colors.text, fontWeight: "600" }}>
              {weather.current?.temperature_2m} °C · rain {weather.current?.precipitation} mm · risk {weather.weather_risk_level?.toLowerCase()}
            </Text>
            {weather.reasons?.map((r) => <Muted key={r}>• {r}</Muted>)}
            <Muted style={{ fontSize: 11, marginTop: 4 }}>Weather data by Open-Meteo.com</Muted>
          </Card>
        )}

        <Card>
          <Label>Trip</Label>
          {status?.active_trip ? (
            <>
              <Text style={{ fontWeight: "600", color: colors.text, fontSize: 16 }}>{status.active_trip.title}</Text>
              <Muted>{status.active_trip.destination ?? "No destination set"} · started {timeAgo(status.active_trip.started_at)}</Muted>
            </>
          ) : (
            <Muted>No active trip.</Muted>
          )}
          <Button title={status?.active_trip ? "Manage trip" : "Start a trip"} variant="secondary" onPress={() => router.push("/trip")} style={{ marginTop: 12 }} />
        </Card>

        {!!status?.zones?.nearby.length && (
          <Card>
            <Label>Nearby safety information</Label>
            {status.zones.nearby.map((z) => (
              <Row key={z.zone_id} label={z.zone_name} value={`${Math.round(z.distance_meters)} m`} />
            ))}
          </Card>
        )}

        <Button title="SOS — request emergency help" variant="danger" onPress={() => router.push("/sos")} style={{ minHeight: 60 }} />
        <View style={{ flexDirection: "row", gap: 10 }}>
          <Button title={`Alerts${status?.unread_notifications ? ` (${status.unread_notifications})` : ""}`} variant="secondary" onPress={() => router.push("/alerts")} style={{ flex: 1 }} />
          <Button title="Safety report" variant="secondary" onPress={() => router.push("/report")} style={{ flex: 1 }} />
        </View>
      </ScrollView>
    </Screen>
  );
}
