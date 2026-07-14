import { useState } from "react";
import {
  MonitorCog,
  Database,
  TrafficCone,
  Construction,
  RadioTower,
  Zap,
  Thermometer,
  DoorOpen,
  Landmark,
  Flame,
  Wrench,
  TrainFront,
} from "lucide-react";

function RailroadMap({
  devices = [],
  incidents = [],
  trains = [],
  trackBlocks = [],
}) {
  const [selectedAsset, setSelectedAsset] = useState(null);

  const getDevice = (name) =>
    devices.find((device) => device.name === name);

  const getStatusClass = (device) => {
    if (!device) return "unknown";

    if (
      device.status === "Offline" ||
      device.status === "Degraded"
    ) {
      return "offline";
    }

    const risk = device.calculated_risk || device.risk_level;

    if (risk === "Critical") return "critical";
    if (risk === "High") return "warning";
    if (risk === "Medium") return "medium";

    return "healthy";
  };

  const getIncidentCount = (assetName) =>
    incidents.filter(
      (incident) =>
        incident.device === assetName &&
        incident.status !== "Closed"
    ).length;

  const getBlockClass = (block) => {
    if (!block) return "unknown";
    return block.occupied ? "occupied" : "clear";
  };

  const getTrainPosition = (milepost) => {
    const minimumMilepost = 80.0;
    const maximumMilepost = 95.2;

    const trackStartPercent = 12;
    const trackEndPercent = 88;

    const value = Number(milepost);

    if (!Number.isFinite(value)) {
      return trackStartPercent;
    }

    const progress =
      (value - minimumMilepost) /
      (maximumMilepost - minimumMilepost);

    const clampedProgress = Math.max(
      0,
      Math.min(1, progress)
    );

    return (
      trackStartPercent +
      clampedProgress *
        (trackEndPercent - trackStartPercent)
    );
  };

  const fallbackBlocks = [
    {
      id: 1,
      name: "Block A",
      start_mp: 80.0,
      end_mp: 82.4,
      occupied: false,
      occupied_by: null,
    },
    {
      id: 2,
      name: "Block B",
      start_mp: 82.4,
      end_mp: 87.1,
      occupied: false,
      occupied_by: null,
    },
    {
      id: 3,
      name: "Block C",
      start_mp: 87.1,
      end_mp: 95.2,
      occupied: false,
      occupied_by: null,
    },
  ];

  const displayedBlocks =
    trackBlocks.length > 0
      ? trackBlocks
      : fallbackBlocks;

  const mapAssets = [
    {
      name: "Dispatch SCADA Server",
      label: "Dispatch Center",
      icon: MonitorCog,
      position: "dispatch",
    },
    {
      name: "Operations Historian",
      label: "Historian",
      icon: Database,
      position: "historian",
    },
    {
      name: "Signal Controller 14A",
      label: "Signal 14A",
      icon: TrafficCone,
      position: "signal-a",
    },
    {
      name: "Signal Controller 14B",
      label: "Signal 14B",
      icon: TrafficCone,
      position: "signal-b",
    },
    {
      name: "Grade Crossing Controller MP 82.4",
      label: "Crossing MP 82.4",
      icon: Construction,
      position: "crossing-a",
    },
    {
      name: "PTC Radio Gateway",
      label: "PTC Radio",
      icon: RadioTower,
      position: "ptc",
    },
    {
      name: "UPS System",
      label: "UPS Power",
      icon: Zap,
      position: "ups",
    },
    {
      name: "Hydrogen Gas Detector",
      label: "Gas Detector",
      icon: Thermometer,
      position: "gas",
    },
    {
      name: "Cabinet Intrusion Sensor",
      label: "Cabinet Sensor",
      icon: DoorOpen,
      position: "cabinet",
    },
    {
      name: "Bridge Structural Monitor",
      label: "Bridge Monitor",
      icon: Landmark,
      position: "bridge",
    },
    {
      name: "Hot Bearing Detector",
      label: "Hot Bearing",
      icon: Flame,
      position: "bearing",
    },
    {
      name: "Rail Engineering Workstation",
      label: "Engineering",
      icon: Wrench,
      position: "maintenance",
    },
  ];

  return (
    <section className="rail-ops-map">
      <div className="rail-map-header">
        <h2>Interactive Railroad Operations Map</h2>

        <p>
          Simulated rail subdivision showing live OT asset health,
          cyber risk, safety sensors, infrastructure monitoring,
          train movement, and block occupancy.
        </p>
      </div>

      <div className="subdivision-map expanded">
        
        
        {/* Main track occupancy blocks */}
        <div className="track-blocks">
  {displayedBlocks.map((block) => (
    <div
      key={block.id}
      className={`track-block ${
        block.occupied ? "occupied" : "clear"
      }`}
    >
      <span className="track-block-name">
        {block.name}
      </span>

      <span className="track-block-status">
        {block.occupied
          ? `Occupied: ${block.occupied_by || "Unknown"}`
          : "Clear"}
      </span>

      {/* DEBUG */}
      <small
        style={{
          color: "white",
          display: "block",
          marginTop: "18px",
          fontSize: "10px",
        }}
      >
        occupied = {String(block.occupied)}
      </small>

    </div>
  ))}
</div>

        {/* Siding */}
        <div className="track-line siding-track"></div>

        {/* Moving trains */}
        {trains.map((train) => (
          <div
            key={train.id}
            className={`train-marker ${
              train.direction?.toLowerCase() || "unknown"
            }`}
            style={{
              left: `${getTrainPosition(
                train.milepost
              )}%`,
            }}
          >
            <div className="train-icon">
              <TrainFront
                size={34}
                strokeWidth={1.8}
                aria-hidden="true"
              />
            </div>

            <div className="train-label">
              <strong>
                {train.symbol || "Unknown Train"}
              </strong>

              <span>
                {train.direction ||
                  "Unknown Direction"}
              </span>

              <span>
                MP{" "}
                {Number.isFinite(
                  Number(train.milepost)
                )
                  ? Number(
                      train.milepost
                    ).toFixed(2)
                  : "Unknown"}
              </span>

              <span>
                {train.speed ?? 0} MPH
              </span>

              <span>
                {train.status || "Unknown Status"}
              </span>
            </div>
          </div>
        ))}

        {/* Track ties */}
        <div className="track-tie tie-1"></div>
        <div className="track-tie tie-2"></div>
        <div className="track-tie tie-3"></div>
        <div className="track-tie tie-4"></div>
        <div className="track-tie tie-5"></div>
        <div className="track-tie tie-6"></div>

        {/* Mileposts */}
        <div className="milepost mp80">
          <div className="milepost-marker"></div>
          <span>MP 80.0</span>
        </div>

        <div className="milepost mp824">
          <div className="milepost-marker"></div>
          <span>MP 82.4</span>
        </div>

        <div className="milepost mp871">
          <div className="milepost-marker"></div>
          <span>MP 87.1</span>
        </div>

        <div className="milepost mp952">
          <div className="milepost-marker"></div>
          <span>MP 95.2</span>
        </div>

        {/* Railroad OT assets */}
        {mapAssets.map((asset) => {
          const device = getDevice(asset.name);
          const statusClass =
            getStatusClass(device);
          const activeIncidentCount =
            getIncidentCount(asset.name);
          const AssetIcon = asset.icon;

          console.log("Track Blocks:", displayedBlocks);
          console.log("APP trackBlocks:", trackBlocks);
          return (
            <button
              key={asset.name}
              className={`map-asset ${asset.position} ${statusClass}`}
              onClick={() => {
                if (device) {
                  setSelectedAsset(device);
                }
              }}
              type="button"
            >
              <span className="map-asset-icon">
                <AssetIcon
                  size={22}
                  strokeWidth={1.8}
                  aria-hidden="true"
                />
              </span>

              <span className="map-asset-label">
                {asset.label}
              </span>

              <span className="map-asset-status">
                {device?.status || "Unknown"}
              </span>

              {activeIncidentCount > 0 && (
                <span className="map-incident-badge">
                  {activeIncidentCount} incident
                  {activeIncidentCount > 1
                    ? "s"
                    : ""}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="map-legend">
        <span>
          <i className="legend-dot healthy"></i>
          Healthy
        </span>

        <span>
          <i className="legend-dot warning"></i>
          Elevated Risk
        </span>

        <span>
          <i className="legend-dot critical"></i>
          Critical / Offline
        </span>

        <span>
          <i className="legend-dot unknown"></i>
          Unknown
        </span>

        <span>
          <i className="legend-dot clear"></i>
          Clear Track
        </span>

        <span>
          <i className="legend-dot occupied"></i>
          Occupied Track
        </span>
      </div>

      {selectedAsset && (
        <div className="rail-asset-panel">
          <div className="rail-asset-panel-header">
            <div>
              <h3>{selectedAsset.name}</h3>
              <p>
                {selectedAsset.device_type}
              </p>
            </div>

            <button
              type="button"
              onClick={() =>
                setSelectedAsset(null)
              }
              aria-label="Close asset details"
            >
              ×
            </button>
          </div>

          <div className="asset-detail-grid">
            <p>
              <strong>Status:</strong>{" "}
              {selectedAsset.status}
            </p>

            <p>
              <strong>Risk:</strong>{" "}
              {selectedAsset.calculated_risk ||
                selectedAsset.risk_level}
            </p>

            <p>
              <strong>IP Address:</strong>{" "}
              {selectedAsset.ip_address}
            </p>

            <p>
              <strong>Vendor:</strong>{" "}
              {selectedAsset.vendor}
            </p>

            <p>
              <strong>Firmware:</strong>{" "}
              {selectedAsset.firmware_version}
            </p>

            <p>
              <strong>Location:</strong>{" "}
              {selectedAsset.location}
            </p>

            <p>
              <strong>Active Incidents:</strong>{" "}
              {getIncidentCount(
                selectedAsset.name
              )}
            </p>

            <p>
              <strong>
                Last Communication:
              </strong>{" "}
              {selectedAsset.last_seen
                ? new Date(
                    selectedAsset.last_seen
                  ).toLocaleString()
                : "Unknown"}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

export default RailroadMap;