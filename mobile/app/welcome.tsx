import { router } from "expo-router";
import { Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button, colors } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const POINTS = [
  ["Live safety status", "See whether you are near a restricted or high-risk zone."],
  ["One-tap SOS", "Alert the monitoring team and police with your exact location."],
  ["You stay in control", "Location is shared only after you consent, and you can delete your history."],
];

export default function Welcome() {
  const { sessionExpired } = useAuth();
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.ink }}>
      <View style={{ flex: 1, padding: 28, justifyContent: "space-between" }}>
        <View style={{ marginTop: 32 }}>
          <Text style={{ color: "#14917c", fontWeight: "700", letterSpacing: 2, fontSize: 12 }}>SAFETRAIL</Text>
          <Text style={{ color: "#fff", fontSize: 32, fontWeight: "700", marginTop: 12, lineHeight: 38 }}>
            Travel with a safety team watching your back.
          </Text>
          <View style={{ marginTop: 36, gap: 20 }}>
            {POINTS.map(([title, body]) => (
              <View key={title} style={{ flexDirection: "row", gap: 14 }}>
                <View style={{ width: 4, borderRadius: 2, backgroundColor: "#14917c" }} />
                <View style={{ flex: 1 }}>
                  <Text style={{ color: "#fff", fontWeight: "600", fontSize: 16 }}>{title}</Text>
                  <Text style={{ color: "#8ea0aa", marginTop: 4, lineHeight: 20 }}>{body}</Text>
                </View>
              </View>
            ))}
          </View>
        </View>
        <View style={{ gap: 12 }}>
          {sessionExpired && <Text style={{ color: "#fbbf24", textAlign: "center" }}>Your session ended. Please sign in again.</Text>}
          <Button title="Sign in with Gmail" onPress={() => router.push("/login")} />
          <Button title="Server connection" variant="secondary" onPress={() => router.push("/server")} />
          <Text style={{ color: "#8ea0aa", textAlign: "center", fontSize: 12 }}>
            Only Gmail addresses registered by your administrator can sign in.
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
}
