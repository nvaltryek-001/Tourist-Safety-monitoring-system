import { useState } from "react";
import { Linking, ScrollView } from "react-native";
import { Button, Card, ErrorText, Input, Label, Muted, Screen } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Contacts() {
  const { profile, refreshProfile } = useAuth();
  const [name, setName] = useState(profile?.emergency_contact_name ?? "");
  const [phone, setPhone] = useState(profile?.emergency_contact_phone ?? "");
  const [email, setEmail] = useState(profile?.emergency_contact_email ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function save() {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await api("/api/v1/me", {
        method: "PATCH",
        body: { emergency_contact_name: name.trim() || null, emergency_contact_phone: phone.trim() || null, emergency_contact_email: email.trim() || null },
      });
      await refreshProfile();
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} keyboardShouldPersistTaps="handled">
        <Card style={{ gap: 10 }}>
          <Label>Your emergency contact</Label>
          <Muted>When you send an SOS, this contact is emailed if email delivery is configured on the server.</Muted>
          <Input value={name} onChangeText={setName} placeholder="Name" />
          <Input value={phone} onChangeText={setPhone} placeholder="Phone" keyboardType="phone-pad" />
          <Input value={email} onChangeText={setEmail} placeholder="Email" keyboardType="email-address" autoCapitalize="none" />
          <ErrorText message={error} />
          {saved && <Muted>Saved.</Muted>}
          <Button title="Save contact" onPress={save} loading={busy} />
          {!!phone.trim() && <Button title={`Call ${name || "contact"}`} variant="secondary" onPress={() => Linking.openURL(`tel:${phone.trim()}`)} />}
        </Card>
        <Card style={{ gap: 8 }}>
          <Label>Emergency numbers (India)</Label>
          <Button title="112 · All emergencies" variant="secondary" onPress={() => Linking.openURL("tel:112")} />
          <Button title="100 · Police" variant="secondary" onPress={() => Linking.openURL("tel:100")} />
          <Button title="108 · Ambulance" variant="secondary" onPress={() => Linking.openURL("tel:108")} />
          <Button title="1363 · Tourist helpline" variant="secondary" onPress={() => Linking.openURL("tel:1363")} />
        </Card>
      </ScrollView>
    </Screen>
  );
}
