import { useCallback, useEffect, useMemo, useState } from "react";
import "./RailroadMap.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const REFRESH_INTERVAL_MS = 3000;

function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

function getBlockState(block) {
  const communications = normalize(block.communications_status);
  const security = normalize(block.security_status);
  const signal = normalize(block.signal_aspect);

  if (
    communications &&
    !["online", "normal", "healthy"].includes(communications)
  ) {
    return "communications";
  }

  if (block.maintenance) {
    return "maintenance";
  }

  if (
    security &&
    !["healthy", "normal", "low"].includes(security)
  ) {
    return "security";
  }

  if (block.occupied) {
    return "occupied";
  }

  if (signal === "stop" || signal === "dark") {
    return "stop";
  }

  if (
    signal === "approach" ||
    signal === "restricting" ||
    signal === "restricted"
  ) {
    return "approach";
  }

  return "clear";
}

function getSignalSymbol(signalAspect) {
  const signal = normalize(signalAspect);

  if (signal === "stop") {
    return "●";
  }

  if (
    signal === "approach" ||
    signal === "restricting" ||
    signal === "restricted"
  ) {
    return "●";
  }

  if (signal === "dark") {
    return "○";
  }

  return "●";
}

function formatMilepost(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toFixed(1);
}

function formatTimestamp(value) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}

function getTrainPosition(train, minimumMilepost, maximumMilepost) {
  const milepost = Number(train.milepost);

  if (
    !Number.isFinite(milepost) ||
    maximumMilepost <= minimumMilepost
  ) {
    return 0;
  }

  const percentage =
    ((milepost - minimumMilepost) /
      (maximumMilepost - minimumMilepost)) *
    100;

  return Math.min(100, Math.max(0, percentage));
}

function getDirectionArrow(direction) {
  return normalize(direction) === "westbound" ? "←" : "→";
}
function getAssetIcon(device) {
  const name = normalize(device.name);
  const type = normalize(device.device_type);

  if (name.includes("scada") || type.includes("scada")) {
    return "🖥️";
  }

  if (
    name.includes("bridge") ||
    type.includes("infrastructure")
  ) {
    return "🌉";
  }

  if (
    name.includes("crossing") ||
    type.includes("crossing")
  ) {
    return "🚧";
  }

  if (
    name.includes("signal") ||
    type.includes("signal")
  ) {
    return "🚦";
  }

  if (
    name.includes("ptc") ||
    name.includes("radio") ||
    type.includes("communications")
  ) {
    return "📡";
  }

  if (
    name.includes("hot box") ||
    name.includes("bearing")
  ) {
    return "🔥";
  }

  if (
    name.includes("aei") ||
    name.includes("reader")
  ) {
    return "📷";
  }

  if (
    name.includes("weather") ||
    type.includes("environmental")
  ) {
    return "🌦️";
  }

  if (
    name.includes("power") ||
    name.includes("ups") ||
    type.includes("power")
  ) {
    return "⚡";
  }

  if (
    name.includes("engineering") ||
    type.includes("workstation")
  ) {
    return "💻";
  }

  if (
    name.includes("historian") ||
    type.includes("historian")
  ) {
    return "📊";
  }

  if (
    name.includes("firewall") ||
    name.includes("security")
  ) {
    return "🛡️";
  }

  if (
    name.includes("camera") ||
    type.includes("physical security")
  ) {
    return "📹";
  }

  if (
    name.includes("fire") ||
    type.includes("safety")
  ) {
    return "🚨";
  }

  return "⚙️";
}

function getAssetState(device) {
  const status = normalize(device.status);
  const risk = normalize(
    device.calculated_risk ||
      device.risk_level,
  );

  if (
    status === "offline" ||
    risk === "critical"
  ) {
    return "critical";
  }

  if (
    status === "degraded" ||
    risk === "high"
  ) {
    return "warning";
  }

  if (
    status === "online" &&
    ["low", "normal", "healthy", ""].includes(risk)
  ) {
    return "healthy";
  }

  return "unknown";
}

function extractDeviceMilepost(device) {
  const searchableText = [
    device.name,
    device.location,
  ]
    .filter(Boolean)
    .join(" ");

  const match = searchableText.match(
    /\bMP\s*([0-9]+(?:\.[0-9]+)?)/i,
  );

  if (!match) {
    return null;
  }

  const milepost = Number(match[1]);

  return Number.isFinite(milepost)
    ? milepost
    : null;
}

function getKnownDeviceMilepost(device) {
  const name = normalize(device.name);

  const knownLocations = {
    "signal controller 14a": 80.5,
    "grade crossing controller mp 82.4": 82.4,
    "ptc radio gateway": 94.5,
    "dispatch scada server": 80.2,
    "rail engineering workstation": 98.0,
  };

  return knownLocations[name] ?? null;
}

function getDevicePosition(
  device,
  index,
  deviceCount,
  minimumMilepost,
  maximumMilepost,
) {
  const explicitMilepost =
    extractDeviceMilepost(device);

  const knownMilepost =
    getKnownDeviceMilepost(device);

  const milepost =
    explicitMilepost ?? knownMilepost;

  if (
    milepost !== null &&
    maximumMilepost > minimumMilepost
  ) {
    const percentage =
      ((milepost - minimumMilepost) /
        (maximumMilepost - minimumMilepost)) *
      100;

    return Math.min(
      97,
      Math.max(3, percentage),
    );
  }

  const name = normalize(device.name);
  const type = normalize(device.device_type);

  if (
    name.includes("dispatch") ||
    type.includes("scada") ||
    type.includes("historian") ||
    type.includes("jump server")
  ) {
    return 6 + index * 3;
  }

  if (
    name.includes("engineering") ||
    name.includes("maintenance")
  ) {
    return 88 + (index % 3) * 3;
  }

  if (deviceCount <= 1) {
    return 50;
  }

  return (
    8 +
    (index / (deviceCount - 1)) * 84
  );
}

function RailAssetMarker({
  device,
  index,
  deviceCount,
  minimumMilepost,
  maximumMilepost,
  onSelect,
}) {
  const left = getDevicePosition(
    device,
    index,
    deviceCount,
    minimumMilepost,
    maximumMilepost,
  );

  const state = getAssetState(device);

  const placement = index % 2 === 0 ? "above" : "below";

  return (
    <button
      type="button"
      className={`rail-asset-marker rail-asset-marker--${state} rail-asset-marker--${placement}`}
      style={{
        left: `${left}%`,
      }}
      onClick={() => onSelect(device)}
      title={`${device.name} — ${
        device.status || "Unknown"
      }`}
    >
      <span className="rail-asset-marker__stem" />

      <span className="rail-asset-marker__body">
        <span className="rail-asset-marker__icon">
          {getAssetIcon(device)}
        </span>

        <span className="rail-asset-marker__label">
          <strong>{device.name}</strong>

          <small>
            {device.status || "Unknown"}
          </small>
        </span>
      </span>
    </button>
  );
}
function BlockCard({ block, isSelected, onSelect }) {
  const state = getBlockState(block);

  return (
    <button
      type="button"
      className={`track-block track-block--${state} ${
        isSelected ? "track-block--selected" : ""
      }`}
      onClick={() => onSelect(block)}
      aria-label={`Open details for ${block.name}`}
    >
      <div className="track-block__top">
        <div>
          <span className="track-block__name">
            {block.name}
          </span>

          <span className="track-block__range">
            MP {formatMilepost(block.start_mp)}–
            {formatMilepost(block.end_mp)}
          </span>
        </div>

        <span
          className={`signal-indicator signal-indicator--${state}`}
          title={block.signal_aspect || "Unknown"}
        >
          {getSignalSymbol(block.signal_aspect)}
        </span>
      </div>

      <div className="track-block__rail">
        <span className="track-block__tie" />
        <span className="track-block__tie" />
        <span className="track-block__tie" />
        <span className="track-block__tie" />
      </div>

      <div className="track-block__status-row">
        <span>{block.signal_aspect || "Unknown"}</span>

        <span>
          {block.occupied
            ? block.occupied_by || "Occupied"
            : "Unoccupied"}
        </span>
      </div>

      <div className="track-block__footer">
        <span>{block.speed_limit || "—"} MPH</span>
        <span>{block.communications_status || "Unknown"}</span>
      </div>
    </button>
  );
}

function TrainMarker({
  train,
  minimumMilepost,
  maximumMilepost,
  onSelect,
}) {
  const left = getTrainPosition(
    train,
    minimumMilepost,
    maximumMilepost,
  );

  return (
    <button
      type="button"
      className="train-marker"
      style={{ left: `${left}%` }}
      onClick={() => onSelect(train)}
      title={`${train.symbol || "Train"} at MP ${
        train.milepost ?? "Unknown"
      }`}
    >
      <span className="train-marker__icon">🚆</span>

      <span className="train-marker__label">
        <strong>{train.symbol || `Train ${train.id}`}</strong>
        <small>
          {getDirectionArrow(train.direction)} MP{" "}
          {formatMilepost(train.milepost)}
        </small>
      </span>
    </button>
  );
}

function MetricCard({ label, value, tone = "neutral" }) {
  return (
    <div className={`map-metric map-metric--${tone}`}>
      <span className="map-metric__label">{label}</span>
      <strong className="map-metric__value">{value}</strong>
    </div>
  );
}

export default function RailroadMap({
  devices = [],
}) {
  const [trackBlocks, setTrackBlocks] = useState([]);
  const [trains, setTrains] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [simulationRunning, setSimulationRunning] =
    useState(false);
  const [selectedBlock, setSelectedBlock] = useState(null);
  const [selectedTrain, setSelectedTrain] = useState(null);
  const [loading, setLoading] = useState(true);
  const [commandPending, setCommandPending] = useState(false);
  const [error, setError] = useState("");

  const fetchJson = useCallback(async (path, options = {}) => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const body = await response.text();

      throw new Error(
        body ||
          `${response.status} ${response.statusText}`,
      );
    }

    return response.json();
  }, []);

  const loadMapData = useCallback(async () => {
    try {
      const [blockData, trainData] = await Promise.all([
        fetchJson("/track-blocks"),
        fetchJson("/trains"),
      ]);

      setTrackBlocks(
        Array.isArray(blockData)
          ? [...blockData].sort(
              (a, b) =>
                Number(a.start_mp) - Number(b.start_mp),
            )
          : [],
      );

      setTrains(Array.isArray(trainData) ? trainData : []);
      setError("");
    } catch (loadError) {
      console.error("Map data load failed:", loadError);
      setError(
        loadError.message ||
          "Unable to load railroad map data.",
      );
    } finally {
      setLoading(false);
    }
  }, [fetchJson]);

  const loadSimulationStatus = useCallback(async () => {
    try {
      const status = await fetchJson(
        "/train-simulation/status",
      );

      setSimulationRunning(
        Boolean(
          status.running ??
            status.is_running ??
            status.active,
        ),
      );
    } catch (statusError) {
      console.warn(
        "Simulation status endpoint unavailable:",
        statusError,
      );
    }
  }, [fetchJson]);

  useEffect(() => {
    loadMapData();
    loadSimulationStatus();

    const refreshTimer = window.setInterval(() => {
      loadMapData();
      loadSimulationStatus();
    }, REFRESH_INTERVAL_MS);

    return () => window.clearInterval(refreshTimer);
  }, [loadMapData, loadSimulationStatus]);

  const runSimulationCommand = async (command) => {
    setCommandPending(true);

    try {
      await fetchJson(`/train-simulation/${command}`, {
        method: "POST",
      });

      await Promise.all([
        loadMapData(),
        loadSimulationStatus(),
      ]);

      setError("");
    } catch (commandError) {
      console.error(
        `Simulation ${command} failed:`,
        commandError,
      );

      setError(
        commandError.message ||
          `Unable to ${command} the simulation.`,
      );
    } finally {
      setCommandPending(false);
    }
  };

  const territory = useMemo(() => {
    if (trackBlocks.length === 0) {
      return {
        minimum: 0,
        maximum: 1,
      };
    }

    return {
      minimum: Math.min(
        ...trackBlocks.map((block) =>
          Number(block.start_mp),
        ),
      ),
      maximum: Math.max(
        ...trackBlocks.map((block) =>
          Number(block.end_mp),
        ),
      ),
    };
  }, [trackBlocks]);

  const metrics = useMemo(() => {
    const occupied = trackBlocks.filter(
      (block) => block.occupied,
    ).length;

    const restrictive = trackBlocks.filter((block) =>
      ["stop", "approach", "restricting", "restricted", "dark"].includes(
        normalize(block.signal_aspect),
      ),
    ).length;

    const communicationsIssues = trackBlocks.filter(
      (block) =>
        !["online", "normal", "healthy"].includes(
          normalize(block.communications_status),
        ),
    ).length;

    const movingTrains = trains.filter((train) =>
      ["moving", "restricted"].includes(
        normalize(train.status),
      ),
    ).length;

    return {
      occupied,
      restrictive,
      communicationsIssues,
      movingTrains,
    };
  }, [trackBlocks, trains]);

  const closeDrawer = () => {
    setSelectedBlock(null);
    setSelectedTrain(null);
    setSelectedDevice(null);
  };

  return (
    <section className="operations-map">
      <header className="operations-map__header">
        <div>
          <p className="operations-map__eyebrow">
            TRACKSENTINEL DIGITAL TERRITORY
          </p>

          <h2>Interactive Railroad Operations Map</h2>

          <p>
            Live train movement, block occupancy, signal
            indications, communications health, and operational
            risk.
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
          onClick={() => runSimulationCommand("start")}
        >
          ▶ Start
        </button>

        <button
          type="button"
          className="map-button"
          disabled={!simulationRunning || commandPending}
          onClick={() => runSimulationCommand("stop")}
        >
          ■ Stop
        </button>

        <button
          type="button"
          className="map-button"
          disabled={commandPending}
          onClick={() => runSimulationCommand("restart")}
        >
          ↻ Restart
        </button>

        <button
          type="button"
          className="map-button"
          disabled={commandPending}
          onClick={() => runSimulationCommand("reset")}
        >
          ⟲ Reset
        </button>

        <button
          type="button"
          className="map-button map-button--refresh"
          disabled={loading}
          onClick={loadMapData}
        >
          Refresh Data
        </button>
      </div>

      {error && (
        <div className="operations-map__error">
          <strong>Map data error:</strong> {error}
        </div>
      )}

      <div className="operations-map__metrics">
        <MetricCard
          label="Active Trains"
          value={trains.length}
        />

        <MetricCard
          label="Moving"
          value={metrics.movingTrains}
          tone="good"
        />

        <MetricCard
          label="Occupied Blocks"
          value={metrics.occupied}
          tone={metrics.occupied > 0 ? "warning" : "good"}
        />

        <MetricCard
          label="Restrictive Signals"
          value={metrics.restrictive}
          tone={metrics.restrictive > 0 ? "warning" : "good"}
        />

        <MetricCard
          label="Communication Issues"
          value={metrics.communicationsIssues}
          tone={
            metrics.communicationsIssues > 0
              ? "critical"
              : "good"
          }
        />
      </div>

      <div className="territory-panel">
        <div className="territory-panel__title-row">
          <div>
            <span className="territory-panel__label">
              PRAIRIE SUBDIVISION
            </span>

            <strong>
              MP {formatMilepost(territory.minimum)}–MP{" "}
              {formatMilepost(territory.maximum)}
            </strong>
          </div>

          <div className="map-legend">
            <span>
              <i className="legend-dot legend-dot--clear" />
              Clear
            </span>

            <span>
              <i className="legend-dot legend-dot--approach" />
              Approach
            </span>

            <span>
              <i className="legend-dot legend-dot--occupied" />
              Occupied
            </span>

            <span>
              <i className="legend-dot legend-dot--issue" />
              Issue
            </span>
          </div>
        </div>

        {loading ? (
          <div className="operations-map__empty">
            Loading railroad territory…
          </div>
        ) : trackBlocks.length === 0 ? (
          <div className="operations-map__empty">
            No track blocks were returned by the API.
          </div>
        ) : (
          <div className="territory-scroll">
            <div
              className="territory-canvas"
              style={{
                minWidth: `${Math.max(
                  trackBlocks.length * 190,
                  1000,
                )}px`,
              }}
            >
              <div className="railroad-territory-lane">
  <div className="railroad-territory-lane__label">
    Main Line and Wayside OT Assets
  </div>

  <div className="railroad-territory-lane__track">
    <div className="railroad-territory-lane__rail railroad-territory-lane__rail--top" />
    <div className="railroad-territory-lane__rail railroad-territory-lane__rail--bottom" />

    <div className="railroad-territory-lane__ties">
      {Array.from({ length: 50 }).map((_, index) => (
        <span key={`tie-${index}`} />
      ))}
    </div>
  </div>

  {devices.map((device, index) => (
    <RailAssetMarker
      key={device.id}
      device={device}
      index={index}
      deviceCount={devices.length}
      minimumMilepost={territory.minimum}
      maximumMilepost={territory.maximum}
      onSelect={(selected) => {
        setSelectedDevice(selected);
        setSelectedTrain(null);
        setSelectedBlock(null);
      }}
    />
  ))}

  {trains.map((train) => (
    <TrainMarker
      key={train.id}
      train={train}
      minimumMilepost={territory.minimum}
      maximumMilepost={territory.maximum}
      onSelect={(selected) => {
        setSelectedTrain(selected);
        setSelectedBlock(null);
        setSelectedDevice(null);
      }}
    />
  ))}
</div>

              <div
                className="track-block-grid"
                style={{
                  gridTemplateColumns: `repeat(${trackBlocks.length}, minmax(170px, 1fr))`,
                }}
              >
                {trackBlocks.map((block) => (
                  <BlockCard
                    key={block.id}
                    block={block}
                    isSelected={
                      selectedBlock?.id === block.id
                    }
                    onSelect={(selected) => {
                      setSelectedBlock(selected);
                      setSelectedTrain(null);
                    }}
                  />
                ))}
              </div>

              <div className="milepost-scale">
                {trackBlocks.map((block) => (
                  <div
                    className="milepost-scale__mark"
                    key={`mp-${block.id}`}
                  >
                    <span />
                    <strong>
                      MP {formatMilepost(block.start_mp)}
                    </strong>
                  </div>
                ))}

                <div className="milepost-scale__mark">
                  <span />
                  <strong>
                    MP {formatMilepost(territory.maximum)}
                  </strong>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {(selectedBlock ||
        selectedTrain ||
        selectedDevice) && (
        <>
          <button
            type="button"
            className="map-drawer-backdrop"
            aria-label="Close details"
            onClick={closeDrawer}
          />

          <aside className="map-drawer">
            <div className="map-drawer__header">
              <div>
                <span className="map-drawer__eyebrow">
                  {selectedBlock
                    ? "TRACK BLOCK"
                    : selectedTrain
                      ? "TRAIN TELEMETRY"
                      : "RAIL OT ASSET"}
                </span>

                <h3>
                  {selectedBlock
                    ? selectedBlock.name
                    : selectedTrain
                      ? selectedTrain.symbol ||
                      `Train ${selectedTrain.id}`
                      : selectedDevice?.name}
                </h3>
              </div>

              <button
                type="button"
                className="map-drawer__close"
                onClick={closeDrawer}
              >
                ×
              </button>
            </div>

            {selectedBlock && (
              <div className="map-drawer__content">
                <div className="drawer-status">
                  <span
                    className={`drawer-status__indicator drawer-status__indicator--${getBlockState(
                      selectedBlock,
                    )}`}
                  />

                  <div>
                    <strong>
                      {selectedBlock.signal_aspect ||
                        "Unknown signal"}
                    </strong>

                    <span>
                      {selectedBlock.occupied
                        ? "Block occupied"
                        : "Block available"}
                    </span>
                  </div>
                </div>

                <dl className="detail-list">
                  <div>
                    <dt>Milepost limits</dt>
                    <dd>
                      {formatMilepost(
                        selectedBlock.start_mp,
                      )}{" "}
                      –{" "}
                      {formatMilepost(selectedBlock.end_mp)}
                    </dd>
                  </div>

                  <div>
                    <dt>Occupied by</dt>
                    <dd>
                      {selectedBlock.occupied_by || "None"}
                    </dd>
                  </div>

                  <div>
                    <dt>Authority</dt>
                    <dd>
                      {selectedBlock.authority || "Unknown"}
                    </dd>
                  </div>

                  <div>
                    <dt>Speed limit</dt>
                    <dd>
                      {selectedBlock.speed_limit || "—"} MPH
                    </dd>
                  </div>

                  <div>
                    <dt>Communications</dt>
                    <dd>
                      {selectedBlock.communications_status ||
                        "Unknown"}
                    </dd>
                  </div>

                  <div>
                    <dt>Security</dt>
                    <dd>
                      {selectedBlock.security_status ||
                        "Unknown"}
                    </dd>
                  </div>

                  <div>
                    <dt>Maintenance</dt>
                    <dd>
                      {selectedBlock.maintenance
                        ? "Active"
                        : "None"}
                    </dd>
                  </div>

                  <div>
                    <dt>Last update</dt>
                    <dd>
                      {formatTimestamp(
                        selectedBlock.last_updated,
                      )}
                    </dd>
                  </div>
                </dl>
              </div>
            )}

            {selectedTrain && (
              <div className="map-drawer__content">
                <div className="drawer-status">
                  <span className="drawer-status__train">
                    🚆
                  </span>

                  <div>
                    <strong>
                      {selectedTrain.status || "Unknown"}
                    </strong>

                    <span>
                      {selectedTrain.direction || "Unknown direction"}
                    </span>
                  </div>
                </div>

                <dl className="detail-list">
                  <div>
                    <dt>Milepost</dt>
                    <dd>
                      MP{" "}
                      {formatMilepost(
                        selectedTrain.milepost,
                      )}
                    </dd>
                  </div>

                  <div>
                    <dt>Speed</dt>
                    <dd>{selectedTrain.speed || 0} MPH</dd>
                  </div>

                  <div>
                    <dt>Signal</dt>
                    <dd>
                      {selectedTrain.current_signal ||
                        "Unknown"}
                    </dd>
                  </div>

                  <div>
                    <dt>Authority</dt>
                    <dd>
                      {selectedTrain.authority || "Unknown"}
                    </dd>
                  </div>

                  <div>
                    <dt>PTC</dt>
                    <dd>
                      {selectedTrain.ptc_enabled
                        ? "Enabled"
                        : "Disabled"}
                    </dd>
                  </div>

                  <div>
                    <dt>Last update</dt>
                    <dd>
                      {formatTimestamp(
                        selectedTrain.last_updated,
                      )}
                    </dd>
                  </div>
                </dl>
              </div>
            )}
            {selectedDevice && (
  <div className="map-drawer__content">
    <div className="drawer-status">
      <span className="drawer-status__asset">
        {getAssetIcon(selectedDevice)}
      </span>

      <div>
        <strong>
          {selectedDevice.status || "Unknown"}
        </strong>

        <span>
          {selectedDevice.device_type ||
            "Rail OT Asset"}
        </span>
      </div>
    </div>

    <dl className="detail-list">
      <div>
        <dt>Asset type</dt>
        <dd>
          {selectedDevice.device_type ||
            "Unknown"}
        </dd>
      </div>

      <div>
        <dt>Location</dt>
        <dd>
          {selectedDevice.location ||
            "Not assigned"}
        </dd>
      </div>

      <div>
        <dt>IP address</dt>
        <dd>
          {selectedDevice.ip_address ||
            "Not available"}
        </dd>
      </div>

      <div>
        <dt>Vendor</dt>
        <dd>
          {selectedDevice.vendor ||
            "Unknown"}
        </dd>
      </div>

      <div>
        <dt>Firmware</dt>
        <dd>
          {selectedDevice.firmware_version ||
            "Unknown"}
        </dd>
      </div>

      <div>
        <dt>Operational status</dt>
        <dd>
          {selectedDevice.status ||
            "Unknown"}
        </dd>
      </div>

      <div>
        <dt>Risk level</dt>
        <dd>
          {selectedDevice.calculated_risk ||
            selectedDevice.risk_level ||
            "Unknown"}
        </dd>
      </div>

      <div>
        <dt>Risk score</dt>
        <dd>
          {selectedDevice.risk_score ?? "—"}
        </dd>
      </div>

      <div>
        <dt>Last seen</dt>
        <dd>
          {formatTimestamp(
            selectedDevice.last_seen,
          )}
        </dd>
      </div>
    </dl>
  </div>
)}
          </aside>
        </>
      )}
    </section>
  );
}