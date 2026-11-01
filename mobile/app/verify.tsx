import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { Button, Card, ErrorText, H1, Input, Label, Muted, Screen, colors } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Verify() {
  const params = useLocalSearchParams<{ email: string; delivery: string; message: string; dev: string; ttl: string }>();
  const { completeLogin } = useAuth();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remaining, setRemaining] = useState(Number(params.ttl || 300));
  const [resent, setResent] = useState<string | null>(null);
  const [devCode, setDevCode] = useState(params.dev || "");

  useEffect(() => {
    const t = setInterval(() => setRemaining((r) => Math.max(0, r - 1)), 1000);
    return () => clearInterval(t);
  }, []);

  async function verify() {
    if (!/^\d{6}$/.test(code)) {
      setError("Enter the 6-digit code.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api<{ access_token: string }>("/api/v1/auth/tourist/verify-otp", {
        method: "POST",
        body: { email: params.email, code, device_name: "SafeTrail mobile" },
      });
      const profile = await completeLogin(res.access_token);
      router.replace(profile?.location_consent_at ? "/home" : "/consent");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      const res = await api<{ message: string; dev_otp?: string; expires_in_seconds: number }>("/api/v1/auth/tourist/request-otp", {
        method: "POST",
        body: { email: params.email },
      });
      setResent(res.message);
      setDevCode(res.dev_otp ?? "");
      setRemaining(res.expires_in_seconds);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not resend");
    }
  }

  const emailed = params.delivery === "ACCEPTED_BY_PROVIDER";
  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 20 }} keyboardShouldPersistTaps="handled">
        <View style={{ gap: 8 }}>
          <H1>Enter your code</H1>
          <Muted>{emailed ? `Sent to ${params.email}.` : params.message}</Muted>
        </View>
        {!!devCode && (
          <Card style={{ backgroundColor: "#fef3c7", borderColor: "#fcd34d" }}>
            <Text style={{ fontWeight: "700", color: "#78350f" }}>Demo mode — email is not configured</Text>
            <Text style={{ color: "#78350f", marginTop: 4 }}>This code was NOT emailed. It is shown here only for demonstration:</Text>
            <Text style={{ fontSize: 28, fontWeight: "700", letterSpacing: 6, color: "#78350f", marginTop: 8 }}>{devCode}</Text>
          </Card>
        )}
        <View>
          <Label>6-digit code</Label>
          <Input
            value={code}
            onChangeText={(t) => setCode(t.replace(/\D/g, "").slice(0, 6))}
            keyboardType="number-pad"
            autoComplete="one-time-code"
            textContentType="oneTimeCode"
            maxLength={6}
            style={{ fontSize: 24, letterSpacing: 8, textAlign: "center" }}
            accessibilityLabel="One-time code"
          />
          <Text style={{ color: remaining ? colors.muted : colors.sos, marginTop: 8, fontSize: 13 }}>
            {remaining ? `Code expires in ${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}` : "Code expired — request a new one."}
          </Text>
          <ErrorText message={error} />
          {resent && <Muted style={{ marginTop: 8 }}>{resent}</Muted>}
        </View>
        <Button title="Verify and continue" onPress={verify} loading={busy} disabled={!remaining} />
        <Button title="Send a new code" variant="ghost" onPress={resend} />
      </ScrollView>
    </Screen>
  );
}
