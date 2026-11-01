import { useCallback, useEffect, useState } from "react";
import { ScrollView, Text } from "react-native";
import { Button, Card, ErrorText, Input, Label, Muted, Screen, colors, timeAgo } from "@/components/ui";
import { api } from "@/lib/api";
import { useLocation } from "@/lib/location";
import type { Trip } from "@/lib/useStatus";

export default function TripScreen() {
  const { background, enableBackground } = useLocation();
  const [trips, setTrips] = useState<Trip[]>([]);
  const [title, setTitle] = useState("");
  const [destination, setDestination] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bgNote, setBgNote] = useState<string | null>(null);
  const active = trips.find((t) => t.status === "ACTIVE");

  const load = useCallback(async () => {
    try {
      setTrips(await api<Trip[]>("/api/v1/me/trips"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load trips");
    }
  }, []);
  useEffect(() => void load(), [load]);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/me/trips", { method: "POST", body: { title: title.trim(), destination: destination.trim() || null } });
      setTitle("");
      setDestination("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start trip");
    } finally {
      setBusy(false);
    }
  }

  async function end(id: number) {
    setBusy(true);
    try {
      await api(`/api/v1/me/trips/${id}/end`, { method: "POST" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not end trip");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} keyboardShouldPersistTaps="handled">
        {active ? (
          <Card style={{ gap: 6 }}>
            <Label>Active trip</Label>
            <Text style={{ fontSize: 20, fontWeight: "700", color: colors.text }}>{active.title}</Text>
            <Muted>{active.destination ?? "No destination"} · started {timeAgo(active.started_at)}</Muted>
            <Button title="End trip" variant="secondary" loading={busy} onPress={() => end(active.id)} style={{ marginTop: 8 }} />
          </Card>
        ) : (
          <Card style={{ gap: 10 }}>
            <Label>Start a trip</Label>
            <Input value={title} onChangeText={setTitle} placeholder="Trip name, e.g. Nandi Hills sunrise" />
            <Input value={destination} onChangeText={setDestination} placeholder="Destination (optional)" />
            <Button title="Start trip" onPress={start} loading={busy} disabled={!title.trim()} />
          </Card>
        )}
        <ErrorText message={error} />
        <Card style={{ gap: 8 }}>
          <Label>Background monitoring</Label>
          <Muted>
            {background
              ? "Location keeps being shared while the app is in the background (a notification shows while active)."
              : "Optional: keep sharing your location while the app is closed during trips. Requires the installed APK; not supported in Expo Go."}
          </Muted>
          {!background && (
            <Button
              title="Enable background location"
              variant="secondary"
              onPress={async () => setBgNote((await enableBackground()) ? null : "Background location was not enabled (permission denied or not supported in this build).")}
            />
          )}
          {bgNote && <Text style={{ color: colors.warn }}>{bgNote}</Text>}
        </Card>
      </ScrollView>
    </Screen>
  );
}
