# Google Maps setup (your own restricted keys)

SafeTrail uses **Google Maps** when a key is configured and falls back to
**OpenStreetMap** automatically when it is not (or when the key fails to load).
No API key is committed to this repository.

## Implementation references
| Surface | Library | Reference |
|---|---|---|
| Admin & police dashboard (Next.js) | `@vis.gl/react-google-maps` + `@googlemaps/markerclusterer` | Google Maps Platform 101 React codelab — `googlemaps-samples/codelab-maps-platform-101-react-js` (APIProvider → Map → AdvancedMarker/Pin, MarkerClusterer from marker refs, imperative `Circle`) |
| Tourist Android app (Expo) | `react-native-maps` with `PROVIDER_GOOGLE` (Maps SDK for Android) | Official Maps SDK for Android samples (`googlemaps-samples/android-samples`) for polygons, circles, markers and polylines |

Adapted code: `dashboard/src/components/google/overlays.tsx` (Circle/Polygon/Polyline/Data layer/Directions in the codelab's pattern) and `dashboard/src/components/google/GoogleMapView.tsx` (clustered tourist and facility markers, SOS markers, GeoJSON zone polygons, open-data layers, info windows, SOS routes).

## 1. Web key (dashboard)
1. Google Cloud Console → create/select a project → **APIs & Services → Enable**: *Maps JavaScript API* and *Directions API*.
2. **Credentials → Create API key**, then **Restrict key**:
   - Application restriction: **Websites** → `http://localhost:3000/*`, `https://<your-project>.vercel.app/*`
   - API restriction: Maps JavaScript API, Directions API
3. Optional: **Map Management → Create Map ID** (JavaScript, Vector) for Advanced Markers in production. Without it the code uses Google's development `DEMO_MAP_ID`.
4. `dashboard/.env.local` (and Vercel → Environment Variables):
   ```
   NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=<your web key>
   NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID=<your map id>   # optional
   ```
5. Restart `npm run dev`. The map legend shows **Map: Google Maps**.

## 2. Android key (APK builds)
Expo Go already contains a Google Maps key, so **no key is needed while testing in Expo Go**.
For an EAS/standalone APK:
1. Enable **Maps SDK for Android**.
2. Create a key restricted to **Android apps** → package `com.safetrail.tourist` + the SHA-1 of your signing certificate (`eas credentials` shows it).
3. Store it as an EAS secret and build:
   ```bash
   eas secret:create --name GOOGLE_MAPS_ANDROID_API_KEY --value <android key>
   eas build -p android --profile preview
   ```
   `mobile/app.config.ts` injects it into `android.config.googleMaps.apiKey` at build time.

## 3. What uses which API
| Feature | API | Billing note |
|---|---|---|
| Base map, markers, circles, polygons, GeoJSON layers | Maps JavaScript API / Maps SDK for Android | map loads |
| SOS route (facility → tourist) on the incident page | Directions API | per request, only when "Show route" is clicked |
| Nearby police/hospitals | **not** Places API — SafeTrail's own OSM facility table | free |
| Phone navigation | Google Maps URL (`/maps/dir/?api=1`) opens the Maps app | free |

## 4. Testing checklist (do this yourself — keys are yours)
**Web**
- [ ] Overview, Live map, Zones, Facilities and an Incident page show Google tiles and the legend says "Google Maps".
- [ ] Tourist markers cluster when zoomed out; clicking opens an info window.
- [ ] Polygon zones and the "Protected areas" layer draw; inactive zones are faint.
- [ ] Incident → Nearest help → **Show route** draws a red driving route with distance/time; with Directions API disabled it shows a dashed line and says so.
- [ ] Remove the key → the same pages show OpenStreetMap.

**Android (Expo Go)**
- [ ] Safety map tab shows Google Maps with your blue location dot.
- [ ] Zones (circles/polygons) and police/hospital pins appear; tapping a pin shows Navigate/Call.
- [ ] Navigate opens the Google Maps app with directions.

Not tested by the assistant: real keys were not available in the build environment, so Google tiles, Directions and Android rendering must be verified with your keys using the checklist above. CI verifies that both apps type-check and build.
