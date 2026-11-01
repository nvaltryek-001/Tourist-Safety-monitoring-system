import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { colors } from "@/components/ui";
import { AuthProvider } from "@/lib/auth";
import { LocationProvider } from "@/lib/location";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <LocationProvider>
          <StatusBar style="dark" />
          <Stack
            screenOptions={{
              headerTintColor: colors.text,
              headerStyle: { backgroundColor: colors.panel },
              headerShadowVisible: false,
              contentStyle: { backgroundColor: colors.bg },
            }}
          >
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="welcome" options={{ headerShown: false }} />
            <Stack.Screen name="login" options={{ title: "Sign in" }} />
            <Stack.Screen name="verify" options={{ title: "Verify email" }} />
            <Stack.Screen name="consent" options={{ title: "Privacy & location" }} />
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="trip" options={{ title: "Active trip" }} />
            <Stack.Screen name="history" options={{ title: "Travel history" }} />
            <Stack.Screen name="report" options={{ title: "Safety report" }} />
            <Stack.Screen name="contacts" options={{ title: "Emergency contacts" }} />
            <Stack.Screen name="settings" options={{ title: "Settings" }} />
            <Stack.Screen name="sos-status/[id]" options={{ title: "Emergency status" }} />
          </Stack>
        </LocationProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
