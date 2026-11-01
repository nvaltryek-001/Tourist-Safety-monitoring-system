import { Redirect } from "expo-router";
import { ActivityIndicator, Text, View } from "react-native";
import { colors } from "@/components/ui";
import { useAuth } from "@/lib/auth";

/** Splash: decides where to go once the stored session has been checked. */
export default function Splash() {
  const { ready, signedIn } = useAuth();
  if (!ready) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.ink, alignItems: "center", justifyContent: "center", gap: 16 }}>
        <Text style={{ color: "#fff", fontSize: 28, fontWeight: "700", letterSpacing: -0.5 }}>SafeTrail</Text>
        <Text style={{ color: "#8ea0aa" }}>Tourist safety monitoring</Text>
        <ActivityIndicator color="#14917c" style={{ marginTop: 24 }} />
      </View>
    );
  }
  if (!signedIn) return <Redirect href="/welcome" />;
  return <Redirect href="/home" />;
}
