# TrackSentinel screenshot index

Screenshots are captured at a 1920×1080 desktop viewport using seeded data and an isolated temporary SQLite database. The automation starts Uvicorn on port 8010 and Vite on port 4173, creates one simulated firmware incident, captures the application, stops both processes, and removes its temporary state.

Run from `frontend`:

```bash
npm run screenshots
```

Install the browser once if Playwright requests it:

```bash
npx playwright install chromium
```

| Filename | Page / feature | Capture state |
|---|---|---|
| `dashboard.png` | Dashboard | Active critical incident and environment overview |
| `executive-dashboard.png` | Executive Dashboard | Seeded operational/security summary |
| `digital-twin.png` | Railroad Digital Twin | Train, territory, wayside assets, and simulated incident |
| `dispatcher-console.png` | Dispatcher Operations | Trains, command controls, routes, and recovery |
| `operational-impact.png` | Operational impact | Impact summary from the dispatcher map |
| `network-visibility.png` | Network Visibility | Six zones, 34 nodes, 36 connections, and one degraded asset |
| `purple-team-library.png` | Scenario Builder | Catalog attack cards and MITRE context |
| `incident-center.png` | Incident Center | Open critical incident |
| `incident-analysis.png` | Incident drawer | Rule-based analysis and operational impact |
| `exercise-library.png` | Exercise Center | Eight seeded exercises and mission briefing |
| `exercise-running.png` | Exercise Center | Running exercise with objective diagnostics and scores |
| `exercise-walkthrough.png` | Exercise Center | Revealed instructor answer sheet |
| `device-inventory.png` | OT Assets | Seeded device inventory |
| `custom-ot-devices.png` | OT Assets | Custom-device creation form |
| `live-telemetry.png` | Live Telemetry | Generated plant-status metrics |

**Last updated:** 2026-08-04

The capture script reports every failed filename and exits nonzero if any page cannot be prepared or captured. It does not reset or write to the normal `backend/ot_platform.db`.
