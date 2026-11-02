import type { ConfigContext, ExpoConfig } from "expo/config";

/**
 * Extends app.json. The Google Maps Android key is injected from the
 * environment at build time (EAS secret or local .env) — never committed.
 * Expo Go uses Expo's own Google Maps key, so no key is needed there.
 * Restrict the key in Google Cloud: Android apps -> package com.safetrail.tourist
 * + your signing SHA-1, API -> Maps SDK for Android.
 */
export default ({ config }: ConfigContext): ExpoConfig => {
  const androidKey = process.env.GOOGLE_MAPS_ANDROID_API_KEY || process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const iosKey = process.env.GOOGLE_MAPS_IOS_API_KEY || "";
  return {
    ...(config as ExpoConfig),
    android: {
      ...config.android,
      config: { ...(config.android?.config ?? {}), ...(androidKey ? { googleMaps: { apiKey: androidKey } } : {}) },
    },
    ios: {
      ...config.ios,
      config: { ...(config.ios?.config ?? {}), ...(iosKey ? { googleMapsApiKey: iosKey } : {}) },
    },
  };
};
