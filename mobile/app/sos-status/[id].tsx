import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Alert, RefreshControl, ScrollView, Text, View } from "react-native";
import { Button, Card, Label, Muted, Screen, colors, timeAgo } from "@/components/ui";
import { api } from "@/lib/api";
import { sosStatusText } from "@/lib/status";
import type { SOSAlert } from "@/lib/useStatus";

const STEPS = ["OPEN", "ACKNOWLEDGED", "RESPONDING", "RESOLVED"];

export default function SOSStatus() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [alert, setAlert] = useState<SOSAlert | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setAlert(await api<SOSAlert>(`/api/v1/me/sos/${id}`));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load status");
    }
  }, [id]);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 10000);
    return () => clearInterval(t);
  }, [load]);

  const currentIndex = alert ? STEPS.indexOf(alert.status) : -1;

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} refreshControl={<RefreshControl refreshing={false} onRefresh={load} />}>
        {error && <Text style={{ color: colors.sos }}>{error} — retrying every 10 s.</Text>}
        {alert && (
          <>
            <Card style={{ borderColor: alert.status === "RESOLVED" ? "#86efac" : "#fca5a5" }}>
              <Label>SOS #{alert.id} · confirmed by server</Label>
              <Text style={{ fontSize: 22, fontWeight: "700", color: alert.status === "RESOLVED" ? colors.safe : colors.sosDark }}>{sosStatusText(alert.status)}</Text>
              <Muted style={{ marginTop: 4 }}>Sent {timeAgo(alert.created_at)} · {alert.alert_type.toLowerCase()}</Muted>
              {alert.assigned_officer && (
                <Text style={{ marginTop: 8, color: colors.text }}>
                  Officer: {alert.assigned_officer.name}
                  {alert.assigned_officer.badge_number ? ` (${alert.assigned_officer.badge_number})` : ""}
                </Text>
              )}
            </Card>

            {alert.status !== "CANCELLED" && (
              <Card style={{ gap: 12 }}>
                {STEPS.map((s, i) => (
                  <View key={s} style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
                    <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: i <= currentIndex ? colors.brand : colors.line, alignItems: "center", justifyContent: "center" }}>
                      <Text style={{ color: "#fff", fontSize: 12, fontWeight: "700" }}>{i <= currentIndex ? "✓" : ""}</Text>
                    </View>
                    <Text style={{ color: i <= currentIndex ? colors.text : colors.muted, fontWeight: i === currentIndex ? "700" : "400" }}>{sosStatusText(s)}</Text>
                  </View>
                ))}
              </Card>
            )}

            <Card style={{ gap: 10 }}>
              <Label>Updates</Label>
              {(alert.timeline ?? []).map((e) => (
                <View key={e.id}>
                  <Text style={{ color: colors.text, fontWeight: "600" }}>{e.action.replace(/_/g, " ").toLowerCase()}</Text>
                  <Muted>
                    {e.actor_name ?? "System"} · {timeAgo(e.created_at)}
                  </Muted>
                  {e.note && <Muted>{e.note}</Muted>}
                </View>
              ))}
            </Card>

            {alert.status === "OPEN" && (
              <Button
                title="Cancel this SOS (false alarm)"
                variant="secondary"
                onPress={() =>
                  Alert.alert("Cancel SOS?", "Only cancel if you are safe.", [
                    { text: "Keep SOS active" },
                    {
                      text: "Cancel SOS",
                      style: "destructive",
                      onPress: async () => {
                        try {
                          setAlert(await api<SOSAlert>(`/api/v1/me/sos/${alert.id}/cancel`, { method: "POST" }));
                        } catch (e) {
                          Alert.alert(e instanceof Error ? e.message : "Could not cancel");
                        }
                      },
                    },
                  ])
                }
              />
            )}
          </>
        )}
        {!alert && !error && <Muted>Loading…</Muted>}
      </ScrollView>
    </Screen>
  );
}
