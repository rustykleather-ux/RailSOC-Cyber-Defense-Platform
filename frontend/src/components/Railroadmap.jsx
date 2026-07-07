function RailroadMap({ devices }) {
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
          asset health.
        </p>
      </div>

      <div className="rail-line">
        {assets.map((asset, index) => {
          const device = getDevice(asset);

          return (
            <div className="rail-stop" key={asset}>
              <div className={`rail-node ${getStatusClass(device)}`}>
                🚦
              </div>

              <div className="rail-name">{asset}</div>

              {index < assets.length - 1 && (
                <div className="rail-track"></div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default RailroadMap;