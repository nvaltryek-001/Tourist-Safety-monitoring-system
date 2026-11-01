import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Alert, ScrollView, Switch, Text, View } from "react-native";
import { Button, Card, Label, Muted, Screen, colors, timeAgo } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { registerForPush } from "@/lib/push";

interface SessionRow {
  id: number;
  created_at: string;
  user_agent: string | null;
  current: boolean;
}

export default function Settings() {
  const { profile, refreshProfile } = useAuth();
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [pushNote, setPushNote] = useState<string | null>(null);

  useEffect(() => {
    api<SessionRow[]>("/api/v1/auth/sessions").then(setSessions).catch(() => undefined);
  }, []);

  async function toggle(field: "notify_push" | "notify_email", value: boolean) {
    await api("/api/v1/me", { method: "PATCH", body: { [field]: value } }).catch(() => undefined);
    await refreshProfile();
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
        <Card style={{ gap: 10 }}>
          <Label>Notifications</Label>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <Text style={{ color: colors.text, flex: 1 }}>Push notifications (SOS updates are always sent)</Text>
            <Switch value={profile?.notify_push ?? true} onValueChange={(v) => toggle("notify_push", v)} />
          </View>
          <Muted>{profile?.push_registered ? "This phone is registered for push." : "This phone is not registered for push yet."}</Muted>
          <Button
            title="Register this phone for push"
            variant="secondary"
            onPress={async () => {
              const r = await registerForPush();
              setPushNote(r.ok ? "Registered." : r.reason);
              await refreshProfile();
            }}
          />
          {pushNote && <Muted>{pushNote}</Muted>}
        </Card>
        <Card style={{ gap: 8 }}>
          <Label>Privacy</Label>
          <Button title="Location consent" variant="secondary" onPress={() => router.push("/consent")} />
          <Button
            title="Delete my location history"
            variant="secondary"
            onPress={() =>
              Alert.alert("Delete location history?", "This permanently removes your stored location points from the server.", [
                { text: "Cancel" },
                {
                  text: "Delete",
                  style: "destructive",
                  onPress: async () => {
                    const r = await api<{ deleted: number }>("/api/v1/me/locations", { method: "DELETE" }).catch(() => null);
                    Alert.alert(r ? `Deleted ${r.deleted} points.` : "Could not delete — try again when online.");
                  },
                },
              ])
            }
          />
        </Card>
        <Card style={{ gap: 8 }}>
          <Label>Signed-in devices</Label>
          {sessions.map((s) => (
            <View key={s.id} style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Muted style={{ flex: 1 }}>{s.current ? "This phone" : (s.user_agent ?? "Device").slice(0, 40)} · {timeAgo(s.created_at)}</Muted>
              {!s.current && (
                <Button
                  title="Revoke"
                  variant="ghost"
                  style={{ minHeight: 36 }}
                  onPress={async () => {
                    await api(`/api/v1/auth/sessions/${s.id}/revoke`, { method: "POST" }).catch(() => undefined);
                    setSessions((prev) => prev.filter((x) => x.id !== s.id));
                  }}
                />
              )}
            </View>
          ))}
        </Card>
      </ScrollView>
    </Screen>
  );
}
