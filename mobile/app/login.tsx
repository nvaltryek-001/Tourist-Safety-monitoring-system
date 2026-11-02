import { router } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, View } from "react-native";
import { Button, ErrorText, H1, Input, Label, Muted, Screen } from "@/components/ui";
import { api, apiUrl } from "@/lib/api";
import { isGmail } from "@/lib/status";

interface OTPResponse {
  delivery: string;
  message: string;
  expires_in_seconds: number;
  dev_otp?: string;
}

export default function Login() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    if (!isGmail(email)) {
      setError("Enter the Gmail address your administrator registered (…@gmail.com).");
      return;
    }
    setBusy(true);
    try {
      const res = await api<OTPResponse>("/api/v1/auth/tourist/request-otp", { method: "POST", body: { email: email.trim() } });
      router.push({
        pathname: "/verify",
        params: { email: email.trim(), delivery: res.delivery, message: res.message, dev: res.dev_otp ?? "", ttl: String(res.expires_in_seconds) },
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not request a code");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={{ padding: 24, gap: 20 }} keyboardShouldPersistTaps="handled">
          <View style={{ gap: 8 }}>
            <H1>Sign in</H1>
            <Muted>We will send a 6-digit code to your Gmail inbox. No password is needed.</Muted>
          </View>
          <View>
            <Label>Gmail address</Label>
            <Input
              value={email}
              onChangeText={setEmail}
              placeholder="yourname@gmail.com"
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              returnKeyType="send"
              onSubmitEditing={submit}
              accessibilityLabel="Gmail address"
            />
            <ErrorText message={error} />
          </View>
          <Button title="Send login code" onPress={submit} loading={busy} />
          <Muted>
            Your administrator must first add your Gmail under Dashboard → Tourist login access. Not approved yet? Ask them — new Gmail
            addresses cannot sign themselves up.
          </Muted>
          <Button title={`Server: ${apiUrl()}`} variant="ghost" onPress={() => router.push("/server")} />
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}
