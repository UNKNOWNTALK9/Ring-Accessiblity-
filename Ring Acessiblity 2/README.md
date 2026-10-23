# Ring Accessible Alert

A responsive Flask + SQLite hackathon prototype for deaf and hard-of-hearing users. Its core workflow turns a supported event into a large visual alert, a persistent event record, and optional browser vibration where supported.

> (**Demo mode is live Ring connectivity.**): This includes a working simulator adapter. It does claim to connect to a physical Ring device.`ring_adapter.py` is an explicit integration boundary, not a fake API.

## Features implemented

- Responsive dashboard with clear demo/live distinction and connection status.
- Flask JSON API, SQLite persistence, event validation and duplicate-ID protection.
- Built-in demo events: doorbell, person, motion, and package/delivery.
- Server-Sent Events stream for connected dashboards.
- Large alert overlay, acknowledge workflow, event list, filters, and history clearing.
- Saved high contrast, large text, extra-large alert, vibration, screen flash, reduced motion, theme, duration, smart display, and emergency-mode preferences.
- Persistent automation rules with supported in-app actions and visible limitation for smart-display delivery.
- Keyboard focus indicators, semantic labels, Escape to dismiss, dialog focus management, and reduced-motion support.
- Automated tests for health, event persistence, validation, acknowledgement, settings, and rule creation.

## Requirements

- Python 3.10+
- A modern browser
- No Ring hardware or paid API required for demo mode

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
python app.py
```

Open http://127.0.0.1:5000. The SQLite database is created automatically.

## Test

```bash
python -m unittest discover -s tests -v
```

Tests use a separate temporary database path.

## Demo script (2–3 minutes)

1. Open **Demo / how it works** and explain the event pipeline.
2. Select **Doorbell pressed**. A full-screen alert appears with large text and a clear simulated-event label.
3. Acknowledge the alert. Show that its status updates and that the record remains in history.
4. Generate **Person detected** and **Package / delivery** events.
5. Open **Event history**, filter by event type, and show persisted events.
6. Open **Accessibility settings**, enable high contrast or large text, save, and refresh the page to show persistence.
7. Open **Automations**, create or disable a rule, then generate the matching event.
8. Open **Ring connection** and clearly explain that live integration is not connected in this demo.

## API endpoints

- `GET /api/health`
- `GET /api/events?limit=100&type=doorbell_pressed&unread=true`
- `POST /api/events/demo` with `{"event_type":"doorbell_pressed"}`
- `PATCH /api/events/<id>/acknowledge`
- `DELETE /api/events` (clears history)
- `GET /api/settings`
- `PUT /api/settings` with partial setting values
- `GET /api/rules`
- `POST /api/rules` with `name`, `event_type`, `actions`
- `PATCH /api/rules/<id>` with `{"enabled":false}`
- `GET /api/ring/status`
- `GET /api/stream` (SSE)
- `GET /api/automation/preview`

## Live Ring integration plan

1. Read the official hackathon integration docs and confirm which API/SDK or simulator is allowed.
2. Confirm supported event delivery (webhook, SDK event stream, polling, etc.) and authentication.
3. Implement `RingAdapter` in `ring_adapter.py` using documented methods only.
4. Translate only real supported events to `event_type`, `event_id`, `device_name`, and optional `description`.
5. Pass normalized events to `process_event(payload, source="ring")`; never label them simulated.
6. Add connection lifecycle, token expiry, retry/backoff, permission errors, and adapter tests.
7. Set `RING_MODE=live` only after the adapter is implemented and verified. The demo event endpoint is disabled in live mode.

This prototype deliberately reports live mode as **not connected** until an approved adapter is actually wired in. `RING_ACCESS_TOKEN` is only a placeholder boundary; no assumed public endpoint is used.

## Current limitations

- **Vibration:** Web Vibration API support is inconsistent and usually requires a user gesture/device/browser support. The app falls back to visible alerts and reports when vibration is unavailable.
- **Smart display:** The preference and automation action are represented, but sending to a real smart display requires a compatible integration.
- **Live feed / Talk / Record / Snapshot:** No real camera media or two-way audio is provided in demo mode. This avoids presenting fake camera content as real. Add these only through a documented, authorized integration.
- **Authentication:** Local development defaults to no login. For shared or deployed environments, enable authentication, add CSRF protection/rate limiting, use HTTPS, configure a strong secret, and review the threat model before exposing the service. The included optional `AUTH_REQUIRED` switch is a minimal gate, not a production identity system.
- **Accessibility:** Designed toward WCAG 2.2 AA practices, but a formal audit with assistive technologies and contrast measurements is still required. Flash cues are optional and should not be the only alert signal.

## Security and privacy

- Do not commit `.env`, database files, Ring tokens, or passwords.
- Use HTTPS for deployment and keep media private.
- Limit event retention and avoid storing visitor identities unless necessary.
- Add CSRF protection and production-grade authentication before internet exposure.
- Never claim emergency detection: emergency mode only changes how configured supported events are presented.
