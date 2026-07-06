function LivePlantStatus({ plantStatus }) {
  const displayName = (name) => {
    switch (name) {
      case "SCADA Server":
        return "Dispatch SCADA Server";

      case "PLC-1":
        return "Signal Controller 14A";

      case "PLC-2":
        return "Grade Crossing Controller MP 82.4";

      case "Solar Inverter":
        return "PTC Radio Gateway";

      case "Engineering Workstation":
        return "Rail Engineering Workstation";

      default:
        return name || "Unknown Asset";
    }
  };

  const displayType = (type) => {
    switch (type) {
      case "PLC":
        return "Signal Control";

      case "SCADA":
        return "Dispatch Operations";

      case "Inverter":
        return "PTC Communications";

      case "Workstation":
        return "Engineering Station";

      default:
        return type || "Rail Asset";
    }
  };

  return (
    <>
      <h2>Live Railroad Asset Status</h2>

      <p className="simulation-subtitle">
        Real-time operational telemetry for simulated railroad infrastructure.
      </p>

      <div className="plant-grid">
        {(plantStatus || []).map((item, index) => (
          <div
            key={index}
            className={`plant-card ${(item.status || "unknown").toLowerCase()}`}
          >
            <h3>{displayName(item.device)}</h3>

            <p className="plant-type">
              {displayType(item.type)}
            </p>

            <p>
              <strong>Status:</strong> {item.status || "Unknown"}
            </p>

            <p>
              <strong>Operational State:</strong>{" "}
              <span
                className={`badge ${
                  item.condition === "Normal" ? "low" : "high"
                }`}
              >
                {item.condition || "Unknown"}
              </span>
            </p>

            {item.temperature !== undefined && (
              <p>
                <strong>Equipment Temperature:</strong>{" "}
                {item.temperature}°F
              </p>
            )}

            {item.power_output_kw !== undefined && (
              <p>
                <strong>Backup Power:</strong>{" "}
                {item.power_output_kw} kW
              </p>
            )}

            {item.voltage !== undefined && (
              <p>
                <strong>Supply Voltage:</strong>{" "}
                {item.voltage} V
              </p>
            )}

            {item.cpu_usage !== undefined && (
              <p>
                <strong>Controller CPU:</strong>{" "}
                {item.cpu_usage}%
              </p>
            )}

            {item.memory_usage !== undefined && (
              <p>
                <strong>Controller Memory:</strong>{" "}
                {item.memory_usage}%
              </p>
            )}

            {item.active_sessions !== undefined && (
              <p>
                <strong>Remote Sessions:</strong>{" "}
                {item.active_sessions}
              </p>
            )}

            {item.failed_logins !== undefined && (
              <p>
                <strong>Failed Authentication:</strong>{" "}
                {item.failed_logins}
              </p>
            )}

            <p>
              <strong>Network Latency:</strong>{" "}
              {item.network_latency ?? "Unknown"} ms
            </p>

            <small>
              Updated{" "}
              {item.timestamp
                ? new Date(item.timestamp).toLocaleTimeString()
                : "Unknown"}
            </small>
          </div>
        ))}
      </div>
    </>
  );
}

export default LivePlantStatus;