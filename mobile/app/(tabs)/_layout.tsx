import { Redirect, Tabs } from "expo-router";
import { Text } from "react-native";
import { colors } from "@/components/ui";
import { useAuth } from "@/lib/auth";

function Glyph({ label, color }: { label: string; color: string }) {
  return <Text style={{ color, fontSize: 18, fontWeight: "700" }}>{label}</Text>;
}

export default function TabsLayout() {
  const { ready, signedIn } = useAuth();
  if (ready && !signedIn) return <Redirect href="/welcome" />;
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.muted,
        headerStyle: { backgroundColor: colors.panel },
        headerShadowVisible: false,
        tabBarStyle: { height: 64, paddingBottom: 10, paddingTop: 6 },
        tabBarLabelStyle: { fontSize: 12, fontWeight: "600" },
      }}
    >
      <Tabs.Screen name="home" options={{ title: "Home", tabBarIcon: ({ color }) => <Glyph label="⌂" color={color} /> }} />
      <Tabs.Screen name="map" options={{ title: "Safety map", tabBarIcon: ({ color }) => <Glyph label="◎" color={color} /> }} />
      <Tabs.Screen
        name="sos"
        options={{
          title: "SOS",
          tabBarActiveTintColor: colors.sos,
          tabBarIcon: ({ color }) => <Glyph label="!" color={color === colors.muted ? colors.sos : color} />,
        }}
      />
      <Tabs.Screen name="alerts" options={{ title: "Alerts", tabBarIcon: ({ color }) => <Glyph label="◉" color={color} /> }} />
      <Tabs.Screen name="profile" options={{ title: "Profile", tabBarIcon: ({ color }) => <Glyph label="☰" color={color} /> }} />
    </Tabs>
  );
}
