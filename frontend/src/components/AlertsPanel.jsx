function AlertsPanel({ alerts }) {
  return (
    <>
      <h2>Active Security Alerts</h2>

      <div className="alerts">
        {(alerts || []).length === 0 ? (
          <div className="alert">
            <strong>No Active Alerts</strong>
          </div>
        ) : (
          (alerts || []).map((alert) => (
            <div
              key={alert.id}
              className={`alert ${(alert.severity || "low").toLowerCase()}`}
            >
              <h3>{alert.device || "Unknown Device"}</h3>

              <strong>Severity:</strong>{" "}
              <span className={`badge ${(alert.severity || "low").toLowerCase()}`}>
                {alert.severity || "Unknown"}
              </span>

              <p>
                <strong>Alert:</strong> {alert.message || "No message"}
              </p>

              <small>
                {alert.time
                  ? new Date(alert.time).toLocaleString()
                  : "Unknown"}
              </small>
            </div>
          ))
        )}
      </div>
    </>
  );
}

export default AlertsPanel;