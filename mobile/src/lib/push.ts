import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import { api } from "./api";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export type PushResult = { ok: true } | { ok: false; reason: string };

/**
 * Registers the Expo push token with the backend. Remote push is not
 * available in Expo Go (SDK 53+) or emulators — the reason is returned so the
 * app can say so instead of pretending notifications work.
 */
export async function registerForPush(): Promise<PushResult> {
  if (!Device.isDevice) return { ok: false, reason: "Push notifications need a physical phone." };
  if (Constants.appOwnership === "expo") {
    return { ok: false, reason: "Remote push is unavailable in Expo Go. In-app alerts still work; install the APK build for push." };
  }
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("safety", {
      name: "Safety alerts",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
    });
  }
  const existing = await Notifications.getPermissionsAsync();
  let granted = existing.granted;
  if (!granted) granted = (await Notifications.requestPermissionsAsync()).granted;
  if (!granted) return { ok: false, reason: "Notification permission was denied." };
  const projectId =
    (Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined)?.eas?.projectId ?? Constants.easConfig?.projectId;
  if (!projectId) return { ok: false, reason: "EAS projectId missing — run `eas init` before building." };
  try {
    const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
    await api("/api/v1/me", { method: "PATCH", body: { expo_push_token: token } });
    return { ok: true };
  } catch (e) {
    return { ok: false, reason: e instanceof Error ? e.message : "Could not register for push." };
  }
}
