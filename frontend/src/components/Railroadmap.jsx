import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import API from "../api";
import { getDigitalTwinMap } from "../services/mapService";
import AssetDetailPanel from "./railroad-map/AssetDetailPanel";
import DigitalTwinSvg from "./railroad-map/DigitalTwinSvg";
import MapControls from "./railroad-map/MapControls";
import MapImpactPanel from "./railroad-map/MapImpactPanel";
import {
  mapDimensions,
  matchesFilters,
  activeMapConsequence,
  snapshotSignatures,
} from "./railroad-map/mapLayout";
import "./RailroadMap.css";

const REFRESH_INTERVAL_MS = 3000;
const emptySnapshot = {
  generated_at: null,
  subdivisions: [],
  blocks: [],
  signals: [],
  trains: [],
  switches: [],
  crossings: [],
  devices: [],
  operational_impact: {},
  timeline: [],
  alerts: [],
  incidents: [],
  dispatch_commands: [],
  dispatch_routes: [],
  operational_restrictions: [],
  route_topology: [],
};
const initialFilters = {
  subdivision: "all",
  track: "all",
  assetType: "all",
  operational: "all",
  security: "all",
  communications: "all",
};
const initialLayers = {
  blocks: true,
  trains: true,
  signals: true,
  switches: true,
  crossings: true,
  devices: true,
  relationships: true,
  mileposts: true,
  impact: true,
};
const collectionByKind = {
  block: "blocks",
  signal: "signals",
  train: "trains",
  switch: "switches",
  crossing: "crossings",
  device: "devices",
};

export default function RailroadMap() {
  const [snapshot, setSnapshot] = useState(emptySnapshot);
  const [filters, setFilters] = useState(initialFilters);
  const [layers, setLayers] = useState(initialLayers);
  const [zoom, setZoom] = useState(1);
  const [selected, setSelected] = useState(null);
  const [highlightedKeys, setHighlightedKeys] = useState(new Set());
  const [changedKeys, setChangedKeys] = useState(new Set());
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [commandPending, setCommandPending] = useState(false);
  const [error, setError] = useState("");
  const signaturesRef = useRef(null);
  const changeTimerRef = useRef(null);

  const loadMap = useCallback(async () => {
    try {
      const next = await getDigitalTwinMap();
      const signatures = snapshotSignatures(next);
      if (signaturesRef.current) {
        const changes = new Set(
          Object.entries(signatures)
            .filter(([key, value]) => signaturesRef.current[key] !== value)
            .map(([key]) => key),
        );
        setChangedKeys(changes);
        window.clearTimeout(changeTimerRef.current);
        changeTimerRef.current = window.setTimeout(
          () => setChangedKeys(new Set()),
          2400,
        );
      }
      signaturesRef.current = signatures;
      setSnapshot(next);
      setSelected((current) => {
        if (!current) return null;
        const collection = next[collectionByKind[current.kind]] ?? [];
        const updated = collection.find(
          (item) => String(item.id) === String(current.data.id),
        );
        return updated ? { ...current, data: updated } : null;
      });
      setError("");
    } catch (loadError) {
      setError(
        loadError.response?.data?.detail ||
          loadError.message ||
          "Unable to load the digital twin map.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSimulationStatus = useCallback(async () => {
    try {
      const response = await API.get("/train-simulation/status");
      setSimulationRunning(Boolean(response.data?.running));
    } catch {
      setSimulationRunning(false);
    }
  }, []);

  useEffect(() => {
    loadMap();
    loadSimulationStatus();
    const timer = window.setInterval(() => {
      loadMap();
      loadSimulationStatus();
    }, REFRESH_INTERVAL_MS);
    return () => {
      window.clearInterval(timer);
      window.clearTimeout(changeTimerRef.current);
    };
  }, [loadMap, loadSimulationStatus]);

  const visibleSubdivisions = useMemo(
    () =>
      filters.subdivision === "all"
        ? snapshot.subdivisions
        : snapshot.subdivisions.filter(
            (item) => item.name === filters.subdivision,
          ),
    [filters.subdivision, snapshot.subdivisions],
  );
  const dimensions = useMemo(
    () => mapDimensions(visibleSubdivisions, zoom),
    [visibleSubdivisions, zoom],
  );
  const unlocatedDevices = snapshot.devices.filter(
    (device) =>
      device.milepost == null &&
      ["all", "device"].includes(filters.assetType) &&
      matchesFilters(device, filters),
  );
  const consequence = activeMapConsequence(snapshot);

  async function simulationCommand(command) {
    setCommandPending(true);
    try {
      await API.post(
        command === "reset" ? "/reset-demo" : `/train-simulation/${command}`,
      );
      await Promise.all([loadMap(), loadSimulationStatus()]);
    } catch (commandError) {
      setError(
        commandError.response?.data?.detail ||
          `Unable to ${command} the train simulation.`,
      );
    } finally {
      setCommandPending(false);
    }
  }

  function resetView() {
    setFilters(initialFilters);
    setLayers(initialLayers);
    setZoom(1);
    setHighlightedKeys(new Set());
    setSelected(null);
  }

  function highlightMetric(metric) {
    const impact = snapshot.operational_impact;
    const keys = new Set();
    if (
      [
        "affected_blocks",
        "blocked_track_miles",
        "track_availability_percent",
      ].includes(metric)
    ) {
      snapshot.blocks
        .filter((block) =>
          impact.affected_block_names?.includes(block.name),
        )
        .forEach((block) => keys.add(`TRACK_BLOCK:${block.id}`));
    }
    if (
      [
        "stopped_trains",
        "slowed_trains",
        "delayed_trains",
        "cumulative_delay_minutes",
        "ptc_restricted_trains",
      ].includes(metric)
    ) {
      const symbols = new Set([
        ...(impact.stopped_train_symbols ?? []),
        ...(impact.slowed_train_symbols ?? []),
      ]);
      snapshot.trains
        .filter(
          (train) =>
            symbols.has(train.symbol) ||
            (metric === "ptc_restricted_trains" &&
              String(train.status).includes("PTC")),
        )
        .forEach((train) => keys.add(`TRAIN:${train.id}`));
    }
    if (metric === "dispatch_availability_percent") {
      snapshot.devices
        .filter((device) =>
          device.capabilities?.includes("controls_dispatch"),
        )
        .forEach((device) => keys.add(`OT_DEVICE:${device.id}`));
    }
    setHighlightedKeys(keys);
  }

  return (
    <section className="operations-map">
      <header className="operations-map__header">
        <div>
          <p className="operations-map__eyebrow">
            TRACKSENTINEL DIGITAL TERRITORY
          </p>
          <h2>Interactive Railroad Digital Twin</h2>
          <p>
            Live schematic territory driven by authoritative block, train,
            wayside, device, cyber, and operational state.
          </p>
        </div>
        <div
          className={`simulation-badge ${
            simulationRunning
              ? "simulation-badge--running"
              : "simulation-badge--stopped"
          }`}
        >
          <span className="simulation-badge__dot" />
          {simulationRunning ? "Simulation Running" : "Simulation Stopped"}
        </div>
      </header>

      <div className="operations-map__toolbar">
        <button
          type="button"
          className="map-button map-button--primary"
          disabled={simulationRunning || commandPending}
          onClick={() => simulationCommand("start")}
        >
          ▶ Start
        </button>
        <button
          type="button"
          className="map-button"
          disabled={!simulationRunning || commandPending}
          onClick={() => simulationCommand("stop")}
        >
          ■ Stop
        </button>
        <button
          type="button"
          className="map-button"
          disabled={commandPending}
          onClick={() => simulationCommand("restart")}
        >
          ↻ Restart
        </button>
        <button
          type="button"
          className="map-button"
          disabled={commandPending}
          onClick={() => simulationCommand("reset")}
        >
          ⟲ Reset operations
        </button>
        <button type="button" className="map-button" onClick={loadMap}>
          Refresh snapshot
        </button>
      </div>

      {error && (
        <div className="operations-map__error" role="alert">
          <strong>Map data error:</strong> {String(error)}
        </div>
      )}

      {consequence && (
        <div
          className={`dt-event-banner dt-event-banner--${String(
            consequence.severity || "info",
          ).toLowerCase()}`}
          aria-live="polite"
        >
          <span>{consequence.title}</span>
          <strong>{consequence.message}</strong>
        </div>
      )}

      <MapControls
        snapshot={snapshot}
        filters={filters}
        onFilters={setFilters}
        layers={layers}
        onLayers={setLayers}
        zoom={zoom}
        onZoom={setZoom}
        onReset={resetView}
      />

      <div className="dt-map-layout">
        <div className="dt-map-column">
          {unlocatedDevices.length > 0 && layers.devices && (
            <section className="dt-control-assets">
              <span>Control center and network assets</span>
              <div>
                {unlocatedDevices.map((device) => (
                  <button
                    type="button"
                    key={device.id}
                    className={
                      changedKeys.has(`OT_DEVICE:${device.id}`)
                        ? "is-changed"
                        : ""
                    }
                    onClick={() =>
                      setSelected({ kind: "device", data: device })
                    }
                  >
                    <strong>{device.name}</strong>
                    <span>
                      {device.status} · {device.risk}
                    </span>
                  </button>
                ))}
              </div>
            </section>
          )}

          <div className="dt-map-scroll" aria-busy={loading}>
            {loading && snapshot.blocks.length === 0 ? (
              <div className="operations-map__empty">
                Loading digital-twin territory…
              </div>
            ) : visibleSubdivisions.length === 0 ? (
              <div className="operations-map__empty">
                No subdivisions match the current filters.
              </div>
            ) : (
              <DigitalTwinSvg
                snapshot={snapshot}
                dimensions={dimensions}
                filters={filters}
                layers={layers}
                selected={selected}
                onSelect={(kind, data) => setSelected({ kind, data })}
                changedKeys={changedKeys}
                highlightedKeys={highlightedKeys}
              />
            )}
          </div>

          <div className="dt-legend" aria-label="Map state legend">
            <span><i className="normal" /> OK / normal</span>
            <span><i className="occupied" /> OCC / occupied</span>
            <span><i className="approach" /> APP / restricted</span>
            <span><i className="stop" /> STOP / unavailable</span>
            <span><i className="maintenance" /> MNT / maintenance</span>
            <span><i className="communications" /> COMMS / degraded</span>
            <span><i className="security" /> SEC / compromised</span>
          </div>
        </div>

        {layers.impact && (
          <MapImpactPanel
            impact={snapshot.operational_impact}
            onMetric={highlightMetric}
          />
        )}
      </div>

      <AssetDetailPanel
        selected={selected}
        snapshot={snapshot}
        onClose={() => setSelected(null)}
      />
    </section>
  );
}
