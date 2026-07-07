import { useState } from "react";

function RailroadMap({ devices }) {
  const [selectedAsset, setSelectedAsset] = useState(null);

  const getDevice = (name) =>
    (devices || []).find((d) => d.name === name);

  const getStatusClass = (device) => {
    if (!device) return "unknown";
    if (device.status === "Offline") return "offline";

    const risk = device.calculated_risk || device.risk_level;

    if (risk === "Critical") return "critical";
    if (risk === "High") return "warning";

    return "healthy";
  };

  const assets = [
    "Dispatch SCADA Server",
    "Signal Controller 14A",
    "Grade Crossing Controller MP 82.4",
    "PTC Radio Gateway",
    "Rail Engineering Workstation",
  ];

  return (
    <section className="rail-map">
      <div className="rail-map-header">
        <h2>Railroad Digital Twin</h2>
        <p>
          Simulated railroad operational technology infrastructure with live
          asset health. Click an asset to inspect details.
        </p>
      </div>

      <div className="rail-line">
        {assets.map((asset, index) => {
          const device = getDevice(asset);

          return (
            <div className="rail-stop" key={asset}>
              <button
                className={`rail-node ${getStatusClass(device)}`}
                onClick={() => setSelectedAsset(device)}
                type="button"
              >
                🚦
              </button>

              <div className="rail-name">{asset}</div>

              {index < assets.length - 1 && <div className="rail-track"></div>}
            </div>
          );
        })}
      </div>

      {selectedAsset && (
        <div className="rail-asset-panel">
          <div className="rail-asset-panel-header">
            <h3>{selectedAsset.name}</h3>
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