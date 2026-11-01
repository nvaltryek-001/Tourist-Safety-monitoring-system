# GPS and location

* **Source:** the phone's own GPS via `expo-location`. No simulated or fixed coordinates anywhere in the app.
* **Consent first:** the backend rejects location uploads (403) until `POST /api/v1/me/consent {granted:true}`; the consent screen explains what is shared, who sees it, why and for how long. Consent can be withdrawn; SOS still works.
* **Permissions:** foreground permission requested after consent; denied / services-off states shown with a link to system settings; re-checked whenever the app returns to the foreground (revocation stops sharing).
* **Interval:** `Accuracy.Balanced`, every 25 m or 30 s — a battery-conscious default for walking tourists.
* **Accuracy:** each fix carries accuracy in metres; the app labels it High (≤15 m), Moderate (≤50 m) or Low.
* **Offline queue:** fixes are stored in AsyncStorage (max 500, newest kept) with a `client_id`; uploaded in batches of 100 via `/api/v1/me/locations/batch`; retries back off 5 s → 5 min. The server ignores replayed `client_id`s and only moves the "latest position" forward in time.
* **Last update:** the home screen shows the last time the server accepted a point and how many are waiting.
* **Background:** optional during trips with `startLocationUpdatesAsync` + Android foreground-service notification. Requires the EAS APK; Expo Go cannot run background location.
* **Stale data:** dashboard greys out markers older than `STALE_LOCATION_MINUTES` (15); the app shows "Location out of date" instead of "Safe".
* **Retention:** `LOCATION_RETENTION_DAYS` (30) — admins can purge; tourists can delete their own history.
