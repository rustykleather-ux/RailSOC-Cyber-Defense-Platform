function LivePlantStatus({ plantStatus }) {
  return (
    <>
      <h2>Live Plant Status</h2>

      <div className="plant-grid">
        {(plantStatus || []).map((item, index) => (
          <div
            key={index}
            className={`plant-card ${(item.status || "unknown").toLowerCase()}`}
          >
            <h3>{item.device || "Unknown Device"}</h3>
            <p className="plant-type">{item.type || "Unknown Type"}</p>

            <p>
              <strong>Status:</strong> {item.status || "Unknown"}
            </p>

            <p>
              <strong>Condition:</strong>{" "}
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
                <strong>Temperature:</strong> {item.temperature}°F
              </p>
            )}

            {item.power_output_kw !== undefined && (
              <p>
                <strong>Power Output:</strong> {item.power_output_kw} kW
              </p>
            )}

            {item.voltage !== undefined && (
              <p>
                <strong>Voltage:</strong> {item.voltage} V
              </p>
            )}

            {item.cpu_usage !== undefined && (
              <p>
                <strong>CPU:</strong> {item.cpu_usage}%
              </p>
            )}

            {item.memory_usage !== undefined && (
              <p>
                <strong>Memory:</strong> {item.memory_usage}%
              </p>
            )}

            {item.active_sessions !== undefined && (
              <p>
                <strong>Active Sessions:</strong> {item.active_sessions}
              </p>
            )}

            {item.failed_logins !== undefined && (
              <p>
                <strong>Failed Logins:</strong> {item.failed_logins}
              </p>
            )}

            <p>
              <strong>Latency:</strong> {item.network_latency ?? "Unknown"} ms
            </p>

            <small>
              Updated:{" "}
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