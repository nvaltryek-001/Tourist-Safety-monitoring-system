import { router } from "expo-router";
import { useState } from "react";
import { ScrollView, Text } from "react-native";
import { Button, Card, ErrorText, H1, Input, Label, Muted, Screen, colors } from "@/components/ui";
import { DEFAULT_API_URL, apiUrl, setApiUrl, testServer } from "@/lib/api";

/**
 * Lets Expo Go users point the app at their PC's backend without rebuilding:
 * type the PC's Wi-Fi IPv4 address (from `ipconfig`) and test the connection.
 */
export default function ServerScreen() {
  const [url, setUrl] = useState(apiUrl());
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function test(save: boolean) {
    setBusy(true);
    setOk(null);
    setError(null);
    try {
      const ms = await testServer(url);
      if (save) {
        const saved = await setApiUrl(url);
        setUrl(saved);
        setOk(`Connected to ${saved} (${ms} ms). Saved.`);
      } else {
        setOk(`Server is healthy (${ms} ms). Tap “Save” to use it.`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connection failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }} keyboardShouldPersistTaps="handled">
        <H1>Server connection</H1>
        <Muted>Enter the address of the SafeTrail backend. On a home PC this is the PC&apos;s Wi-Fi IPv4 address from ipconfig, port 8000.</Muted>
        <Card style={{ gap: 10 }}>
          <Label>Backend address</Label>
          <Input value={url} onChangeText={setUrl} autoCapitalize="none" autoCorrect={false} keyboardType="url" placeholder="192.168.1.10:8000" />
          <ErrorText message={error} />
          {ok && <Text style={{ color: colors.safe, fontWeight: "600" }}>{ok}</Text>}
          <Button title="Test connection" variant="secondary" onPress={() => test(false)} loading={busy} />
          <Button title="Save & use this server" onPress={() => test(true)} loading={busy} />
          <Button title={`Reset to default (${DEFAULT_API_URL})`} variant="ghost" onPress={async () => { setUrl(await setApiUrl(null)); setOk("Reset to the build default."); }} />
        </Card>
        <Card style={{ gap: 6 }}>
          <Label>Checklist if it fails</Label>
          <Muted>1. Phone and PC on the same Wi-Fi (not guest Wi-Fi).</Muted>
          <Muted>2. Backend started with --host 0.0.0.0 --port 8000.</Muted>
          <Muted>3. Windows Firewall: allow Python on private networks.</Muted>
          <Muted>4. Open http://YOUR-PC-IP:8000/health in the phone browser — it must show “healthy”.</Muted>
        </Card>
        <Button title="Done" variant="ghost" onPress={() => router.back()} />
      </ScrollView>
    </Screen>
  );
}
