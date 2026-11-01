import { router } from "expo-router";
import { useRef, useState } from "react";
import { Alert, Animated, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { Button, Card, ErrorText, Label, Muted, Screen, colors } from "@/components/ui";
import { api } from "@/lib/api";
import { useLocation } from "@/lib/location";
import { accuracyLabel } from "@/lib/status";

const TYPES = [
  ["GENERAL", "Need help"],
  ["MEDICAL", "Medical"],
  ["ACCIDENT", "Accident"],
  ["CRIME", "Crime / theft"],
  ["HARASSMENT", "Harassment"],
  ["LOST", "Lost"],
];

interface SOSResponse {
  created: boolean;
  server_confirmed: boolean;
  alert: { id: number; status: string };
}

export default function SOS() {
  const { currentFix, lastFix } = useLocation();
  const [type, setType] = useState("GENERAL");
  const [stage, setStage] = useState<"idle" | "locating" | "confirm" | "sending" | "failed">("idle");
  const [fix, setFix] = useState(lastFix);
  const [error, setError] = useState<string | null>(null);
  const progress = useRef(new Animated.Value(0)).current;
  const key = useRef<string | null>(null);

  function startHold() {
    Animated.timing(progress, { toValue: 1, duration: 1500, useNativeDriver: false }).start(async ({ finished }) => {
      if (!finished) return;
      setStage("locating");
      setFix(await currentFix());
      key.current = `sos-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
      setStage("confirm");
    });
  }

  function cancelHold() {
    progress.stopAnimation();
    Animated.timing(progress, { toValue: 0, duration: 150, useNativeDriver: false }).start();
  }

  async function send() {
    setStage("sending");
    setError(null);
    try {
      // The same idempotency key is reused on retry so a slow network can never create duplicate alerts.
      const res = await api<SOSResponse>("/api/v1/me/sos", {
        method: "POST",
        timeoutMs: 20000,
        body: {
          latitude: fix?.latitude,
          longitude: fix?.longitude,
          accuracy: fix?.accuracy ?? undefined,
          alert_type: type,
          idempotency_key: key.current,
        },
      });
      if (!res.server_confirmed) throw new Error("The server did not confirm the alert.");
      progress.setValue(0);
      setStage("idle");
      router.push(`/sos-status/${res.alert.id}`);
    } catch (e) {
      setStage("failed");
      setError(e instanceof Error ? e.message : "SOS could not be sent");
    }
  }

  const width = progress.interpolate({ inputRange: [0, 1], outputRange: ["0%", "100%"] });

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
        <Card>
          <Label>What is happening?</Label>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {TYPES.map(([value, label]) => (
              <Pressable
                key={value}
                onPress={() => setType(value)}
                style={{ paddingHorizontal: 14, paddingVertical: 10, borderRadius: 8, borderWidth: 1, borderColor: type === value ? colors.sos : colors.line, backgroundColor: type === value ? "#fee2e2" : colors.panel }}
                accessibilityState={{ selected: type === value }}
              >
                <Text style={{ color: type === value ? colors.sosDark : colors.text, fontWeight: "600" }}>{label}</Text>
              </Pressable>
            ))}
          </View>
        </Card>

        {stage === "confirm" || stage === "sending" || stage === "failed" ? (
          <Card style={{ borderColor: "#fca5a5", gap: 10 }}>
            <Text style={{ fontSize: 20, fontWeight: "700", color: colors.sosDark }}>Send emergency alert?</Text>
            <Muted>
              {fix ? `Your location (${accuracyLabel(fix.accuracy)}) will be sent with the alert.` : "Your location is unavailable — the alert will use your last known position, if any."}
            </Muted>
            <ErrorText message={error} />
            <Button title={stage === "failed" ? "Retry sending SOS" : "Yes, send SOS now"} variant="danger" onPress={send} loading={stage === "sending"} style={{ minHeight: 58 }} />
            <Button title="Cancel" variant="ghost" onPress={() => { setStage("idle"); progress.setValue(0); setError(null); }} disabled={stage === "sending"} />
            {stage === "failed" && (
              <Button title="Call 112 (national emergency number)" variant="secondary" onPress={() => Linking.openURL("tel:112")} />
            )}
          </Card>
        ) : (
          <View style={{ alignItems: "center", gap: 14, marginTop: 12 }}>
            <Pressable
              onPressIn={startHold}
              onPressOut={cancelHold}
              accessibilityRole="button"
              accessibilityLabel="Press and hold to send SOS"
              style={{ width: 220, height: 220, borderRadius: 110, backgroundColor: colors.sos, alignItems: "center", justifyContent: "center", borderWidth: 10, borderColor: "#fecaca", overflow: "hidden" }}
            >
              <Animated.View style={{ position: "absolute", left: 0, bottom: 0, height: "100%", width, backgroundColor: colors.sosDark }} />
              <Text style={{ color: "#fff", fontSize: 44, fontWeight: "800", letterSpacing: 2 }}>SOS</Text>
              <Text style={{ color: "#fee2e2", marginTop: 4 }}>{stage === "locating" ? "Getting location…" : "Press & hold"}</Text>
            </Pressable>
            <Muted style={{ textAlign: "center", paddingHorizontal: 20 }}>
              Hold for 1.5 seconds. You will confirm before anything is sent. The alert is only reported as sent after the server confirms it.
            </Muted>
          </View>
        )}

        <Card>
          <Label>Other options</Label>
          <Button title="Call 112" variant="secondary" onPress={() => Alert.alert("Call 112?", "This calls the national emergency number.", [{ text: "Cancel" }, { text: "Call", onPress: () => Linking.openURL("tel:112") }])} />
          <Button title="Emergency contacts" variant="ghost" onPress={() => router.push("/contacts")} style={{ marginTop: 6 }} />
        </Card>
      </ScrollView>
    </Screen>
  );
}
