import { router } from "expo-router";
import { Alert, ScrollView, Text } from "react-native";
import { Button, Card, Label, Row, Screen, colors } from "@/components/ui";
import { API_URL } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLocation } from "@/lib/location";

export default function Profile() {
  const { profile, logout } = useAuth();
  const { stop } = useLocation();
  const links: [string, string][] = [
    ["Active trip", "/trip"],
    ["Travel history", "/history"],
    ["Safety report", "/report"],
    ["Emergency contacts", "/contacts"],
    ["Privacy & location consent", "/consent"],
    ["Settings", "/settings"],
  ];
  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
        <Card>
          <Text style={{ fontSize: 20, fontWeight: "700", color: colors.text }}>{profile?.name}</Text>
          <Row label="Tourist ID" value={profile?.tourist_code ?? "—"} />
          <Row label="Phone" value={profile?.phone ?? "—"} />
          <Row label="College email" value={profile?.college_email ?? "—"} />
          <Row label="Enrollment" value={profile?.enrollment_number ?? "—"} />
        </Card>
        <Card style={{ gap: 8 }}>
          <Label>More</Label>
          {links.map(([label, href]) => (
            <Button key={href} title={label} variant="secondary" onPress={() => router.push(href as never)} />
          ))}
        </Card>
        <Button
          title="Sign out"
          variant="danger"
          onPress={() =>
            Alert.alert("Sign out?", "Location sharing stops when you sign out.", [
              { text: "Cancel" },
              {
                text: "Sign out",
                style: "destructive",
                onPress: async () => {
                  await stop();
                  await logout();
                  router.replace("/welcome");
                },
              },
            ])
          }
        />
        <Text style={{ textAlign: "center", color: colors.muted, fontSize: 11 }}>Server: {API_URL}</Text>
      </ScrollView>
    </Screen>
  );
}
