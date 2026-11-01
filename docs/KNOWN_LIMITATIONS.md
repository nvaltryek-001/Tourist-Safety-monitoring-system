# Known limitations

* **Real database not inspected.** `tourist_safety.db` is git-ignored, so the 6 tourists / 209 zones / 5 SOS figures come from the 2026-10-17 project-control evidence. Run `python -m app.scripts.audit_db` on the real file to confirm.
* **Original KML files missing** from the repository; their provenance cannot be verified.
* **College demo zone radius** is 200 m in the data vs. the later 50 m request — reported, intentionally not changed.
* **AI** is rule-based and statistically uncalibrated; no ML model is trained (insufficient data).
* **Expo Go:** no background location and no remote push (use the EAS APK). The pinned Expo SDK may need `npx expo install --fix` to match the Expo Go version on your phone.
* **Mobile UI tests** cover pure logic (queue, status, validation) and TypeScript; screens were not run on a physical device in this session.
* **End-to-end** coverage is API-level (tourist login → consent → GPS → restricted entry → alert → SOS → admin → officer acknowledge/resolve → tourist status) inside pytest; there is no browser/device automation (Playwright/Detox).
* **Load testing**: only an in-process smoke test ran; real concurrency numbers need `app/scripts/load_test.py` against a deployed server.
* **Single instance** rate limiting and WebSocket fan-out.
* **SMS** provider is not implemented (Twilio code from v1.0 was replaced by the provider abstraction; SMS is listed as "not configured").
* **Render free tier**: sleeping instances and expiring free PostgreSQL.
* **Dependency audit** (`pip-audit`, `npm audit`) not run in this session.
