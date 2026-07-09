import { useState } from "react";

function RailroadMap({ devices, incidents }) {
  const [selectedAsset, setSelectedAsset] = useState(null);

  const getDevice = (name) => (devices || []).find((d) => d.name === name);

  const getStatusClass = (device) => {
    if (!device) return "unknown";
    if (device.status === "Offline" || device.status === "Degraded")
      return "offline";

    const risk = device.calculated_risk || device.risk_level;

    if (risk === "Critical") return "critical";
    if (risk === "High") return "warning";
    if (risk === "Medium") return "medium";

    return "healthy";
  };

  const getIncidentCount = (assetName) =>
    (incidents || []).filter(
      (incident) => incident.device === assetName && incident.status !== "Closed"
    ).length;

  const mapAssets = [
    {
      name: "Dispatch SCADA Server",
      label: "Dispatch Center",
      icon: "🖥️",
      position: "dispatch",
    },
    {
      name: "Operations Historian",
      label: "Historian",
      icon: "🗄️",
      position: "historian",
    },
    {
      name: "Signal Controller 14A",
      label: "Signal 14A",
      icon: "🚦",
      position: "signal-a",
    },
    {
      name: "Signal Controller 14B",
      label: "Signal 14B",
      icon: "🚦",
      position: "signal-b",
    },
    {
      name: "Grade Crossing Controller MP 82.4",
      label: "Crossing MP 82.4",
      icon: "🚧",
      position: "crossing-a",
    },
    {
      name: "PTC Radio Gateway",
      label: "PTC Radio",
      icon: "📡",
      position: "ptc",
    },
    {
      name: "UPS System",
      label: "UPS Power",
      icon: "⚡",
      position: "ups",
    },
    {
      name: "Hydrogen Gas Detector",
      label: "Gas Detector",
      icon: "🌡️",
      position: "gas",
    },
    {
      name: "Cabinet Intrusion Sensor",
      label: "Cabinet Sensor",
      icon: "🚪",
      position: "cabinet",
    },
    {
      name: "Bridge Structural Monitor",
      label: "Bridge Monitor",
      icon: "🌉",
      position: "bridge",
    },
    {
      name: "Hot Bearing Detector",
      label: "Hot Bearing",
      icon: "🔥",
      position: "bearing",
    },
    {
      name: "Rail Engineering Workstation",
      label: "Engineering",
      icon: "🛠️",
      position: "maintenance",
    },
  ];

  return (
    <section className="rail-ops-map">
      <div className="rail-map-header">
        <h2>Interactive Railroad Operations Map</h2>
        <p>
          Simulated rail subdivision showing live OT asset health, cyber risk,
          safety sensors, infrastructure monitoring, and operational status.
        </p>
      </div>

      <div className="subdivision-map expanded">
        <div className="track-line main-track"></div>
        <div className="track-line siding-track"></div>

        <div className="track-tie tie-1"></div>
        <div className="track-tie tie-2"></div>
        <div className="track-tie tie-3"></div>
        <div className="track-tie tie-4"></div>
        <div className="track-tie tie-5"></div>
        <div className="track-tie tie-6"></div>

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

        {mapAssets.map((asset) => {
          const device = getDevice(asset.name);
          const statusClass = getStatusClass(device);
          const activeIncidentCount = getIncidentCount(asset.name);

          return (
            <button
              key={asset.name}
              className={`map-asset ${asset.position} ${statusClass}`}
              onClick={() => setSelectedAsset(device)}
              type="button"
            >
              <span className="map-asset-icon">{asset.icon}</span>
              <span className="map-asset-label">{asset.label}</span>
              <span className="map-asset-status">
                {device?.status || "Unknown"}
              </span>

              {activeIncidentCount > 0 && (
                <span className="map-incident-badge">
                  {activeIncidentCount} incident
                  {activeIncidentCount > 1 ? "s" : ""}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="map-legend">
        <span><i className="legend-dot healthy"></i> Healthy</span>
        <span><i className="legend-dot warning"></i> Elevated Risk</span>
        <span><i className="legend-dot critical"></i> Critical / Offline</span>
        <span><i className="legend-dot unknown"></i> Unknown</span>
      </div>

      {selectedAsset && (
        <div className="rail-asset-panel">
          <div className="rail-asset-panel-header">
            <div>
              <h3>{selectedAsset.name}</h3>
              <p>{selectedAsset.device_type}</p>
            </div>

            <button onClick={() => setSelectedAsset(null)}>×</button>
          </div>

          <div className="asset-detail-grid">
            <p><strong>Status:</strong> {selectedAsset.status}</p>
            <p><strong>Risk:</strong> {selectedAsset.calculated_risk || selectedAsset.risk_level}</p>
            <p><strong>IP Address:</strong> {selectedAsset.ip_address}</p>
            <p><strong>Vendor:</strong> {selectedAsset.vendor}</p>
            <p><strong>Firmware:</strong> {selectedAsset.firmware_version}</p>
            <p><strong>Location:</strong> {selectedAsset.location}</p>
            <p>
              <strong>Active Incidents:</strong>{" "}
              {getIncidentCount(selectedAsset.name)}
            </p>
            <p>
              <strong>Last Communication:</strong>{" "}
              {selectedAsset.last_seen
                ? new Date(selectedAsset.last_seen).toLocaleString()
                : "Unknown"}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

export default RailroadMap;