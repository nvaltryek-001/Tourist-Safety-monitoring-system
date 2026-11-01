import { router } from "expo-router";
import { useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { Button, Card, ErrorText, H1, Muted, Screen, colors } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLocation } from "@/lib/location";

const ITEMS = [
  ["What is shared", "Your GPS position, its accuracy and time, while sharing is on."],
  ["Who sees it", "Administrators. Police officers only while handling your active SOS."],
  ["Why", "To warn you about restricted zones and to reach you in an emergency."],
  ["How long", "Location history is deleted after the retention period. You can delete yours at any time in Settings."],
  ["Your choice", "You can withdraw consent at any time. SOS still works and sends your location only when you press it."],
];

export default function Consent() {
  const { profile, refreshProfile } = useAuth();
  const { start } = useLocation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const given = !!profile?.location_consent_at;

  async function setConsent(granted: boolean) {
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/me/consent", { method: "POST", body: { granted } });
      await refreshProfile();
      if (granted) {
        const ok = await start();
        if (!ok) setError("Consent saved, but location permission was not granted. You can allow it later from the Home screen.");
        router.replace("/home");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save your choice");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <H1>Location sharing</H1>
        <Muted>SafeTrail uses your phone&apos;s GPS — please read how your location is used.</Muted>
        <Card style={{ gap: 14 }}>
          {ITEMS.map(([t, b]) => (
            <View key={t}>
              <Text style={{ fontWeight: "600", color: colors.text }}>{t}</Text>
              <Text style={{ color: colors.muted, marginTop: 2, lineHeight: 20 }}>{b}</Text>
            </View>
          ))}
        </Card>
        <ErrorText message={error} />
        {given ? (
          <>
            <Muted>You gave consent on {new Date(profile!.location_consent_at!).toLocaleString()}.</Muted>
            <Button title="Withdraw consent" variant="secondary" onPress={() => setConsent(false)} loading={busy} />
            <Button title="Back" variant="ghost" onPress={() => router.back()} />
          </>
        ) : (
          <>
            <Button title="I agree — share my location" onPress={() => setConsent(true)} loading={busy} />
            <Button title="Continue without sharing" variant="ghost" onPress={() => router.replace("/home")} />
          </>
        )}
      </ScrollView>
    </Screen>
  );
}
