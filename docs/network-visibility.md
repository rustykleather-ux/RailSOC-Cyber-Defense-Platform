# Network Visibility design

**Status:** Available · **Scope:** simulation only · [Back to project README](../README.md)

## Purpose

Network Visibility is a simulated IT/OT architecture and telemetry view for
TrackSentinel. It helps cybersecurity analysts see network paths, incidents,
and exposure while helping railroad operators distinguish a direct cyber
effect from a loss of communications or visibility.

It is not a discovery, scanning, packet-capture, or network-control product.

## Trust boundaries

The module accepts data from two approved sources:

1. Existing TrackSentinel SQLAlchemy state, especially linked `OTDevice`
   records and their current status, risk, firmware, address, location, and
   last-seen values.
2. Deterministic or operator-triggered telemetry generated inside the
   TrackSentinel simulation.

The module never reads host interfaces, ARP caches, routing tables, DNS
configuration, or local subnets. It does not send packets, open raw sockets,
invoke shell commands, use nmap or sniffers, change firewall rules, or call
arbitrary HTTP endpoints. External-looking addresses use documentation ranges
and describe simulated nodes only.

Frontend requests are limited to the configured TrackSentinel API base URL
(`VITE_API_BASE_URL`, default `http://127.0.0.1:8000`).
Mutation requests use server-side allow-lists. Unknown actions return a
controlled error and the transaction is rolled back.

## Graph model

The implementation adds five additive SQLAlchemy tables:

- `network_zones`: visible trust and operational boundaries.
- `network_nodes`: infrastructure and OT assets. `ot_device_id` links a node
  to the existing TrackSentinel asset source of truth.
- `network_connections`: simulated relationships with protocol, latency,
  packet loss, bandwidth, encryption, boundary, and status data.
- `network_traffic_events`: compact historical telemetry linked to source,
  target, connection, alert, incident, and optionally a path.
- `network_paths`: saved path-trace results and aggregate health.

Node layout coordinates are presentation state, not network-derived
geolocation. The idempotent seed contains six zones, 34 nodes,
and 36 connections. Startup fills missing static topology
without resetting an active simulated link condition.

## Existing TrackSentinel integration

### Digital twin

Linked network nodes mirror the current `OTDevice` state. Signal, switch,
crossing, PTC, SCADA, and train effects remain owned by the existing
digital-twin and train simulation services. The network layer does not
duplicate or replace those effects.

### Incident Center

Suspicious simulated traffic can create an existing `Alert` and `Incident`.
`NetworkTrafficEvent.related_alert_id` and `related_incident_id` provide the
back-link. The affected OT device is used when one exists; otherwise the
incident identifies the simulated network node by name.

### Exercise and attack simulation

Exercise and attack changes appear through linked device-state synchronization.
Network-specific demonstrations use a strict simulation action catalog and
create the same timeline and incident artifacts used elsewhere.

### Timeline

Path traces, failures, restoration, node actions, suspicious activity, and
layout changes use `services.timeline_service.record_event`. Metadata includes
network entity identifiers and `simulation_only: true`.

## Real-time update strategy

`/ws/network` publishes one validated `network_snapshot` every four seconds.
Each message contains a schema version, simulation marker, generation time,
and structured topology. The React page validates the message type and
simulation marker before using it.

If WebSocket connectivity is unavailable, the frontend polls
`/api/network/topology` every five seconds. It does not continuously run both
mechanisms. Event history is bounded to at most 500 records.

## Path tracing

Path tracing uses deterministic Dijkstra traversal weighted by current
connection latency. Down, blocked, or offline links are excluded.
Bidirectional relationships are traversed in both directions.

Total packet loss is calculated as combined delivery probability:

`loss = 1 - product(1 - per_link_loss)`

The response includes hops, connection IDs, zones, firewalls, protocols,
degraded links, total latency, total loss, and overall path state.

## Dependency and impact behavior

A simulated infrastructure failure may mark a connected asset as Loss of
Communications, Loss of Visibility, Dependency Impact, or Increased Exposure.
It does not mark a downstream asset compromised. Direct compromise remains an
attack or digital-twin decision.

Network baseline restoration clears dependency metadata and restores seeded
link metrics. Linked nodes then re-synchronize with current `OTDevice` state.

## API surface

Read APIs:

- `GET /api/network/nodes`
- `GET /api/network/nodes/{node_id}`
- `GET /api/network/connections`
- `GET /api/network/connections/{connection_id}`
- `GET /api/network/zones`
- `GET /api/network/topology`
- `GET /api/network/traffic`
- `GET /api/network/events`
- `GET /api/network/path`

Validated simulation APIs:

- `POST /api/network/path/trace`
- `POST /api/network/layout`
- `POST /api/network/nodes/{node_id}/{action}`
- `POST /api/network/connections/{connection_id}/{action}`
- `POST /api/network/simulate`
- `POST /api/network/reset`
- `WS /ws/network`

Database mutations are committed at the API boundary. A validation or service
failure rolls the transaction back.

## Performance

React Flow renders only visible graph elements. Topology filtering and
highlight calculations are memoized, WebSocket messages are batched snapshots,
event history is bounded, and node positions are merged rather than reset on
each update. The design target is at least 100 nodes, 250 connections, and 500
recent events.

For larger future deployments, split topology from telemetry deltas, virtualize
the event table, and cache the graph adjacency structure.

## Known limitations

- TrackSentinel has no general user/role framework, so this module follows the
  existing control convention and enforces action allow-lists rather than
  introducing a second authorization system.
- Live updates are full bounded snapshots, not delta streams.
- Alternate path calculation and historical incident replay are future work.
- The graph represents logical simulated relationships, not physical cabling
  or a packet-level protocol model.
- React Flow is currently in the main frontend bundle; route-level lazy loading
  is a recommended optimization.

## Demo

1. Start the FastAPI backend and Vite frontend.
2. Open **Network Visibility** in the sidebar.
3. Select a controller to compare network state with existing OT state.
4. Trace a path from `Vendor Remote Support` to `Signal Controller 14A`.
5. Run `Unauthorized remote access`, `Fiber failure`, or `Network scan`.
6. Review the map, traffic event, Incident Center, and timeline.
7. Select **Restore network baseline** or use the global demo reset.
