import { useState } from "react";

function IncidentCenter({ incidents }) {
  const [selectedIncident, setSelectedIncident] = useState(null);

  return (
    <>
      <h2>Incident Center</h2>

      <div className="incident-center">
        {(incidents || []).length === 0 ? (
          <div className="incident-empty">No active incidents.</div>
        ) : (
          (incidents || []).map((incident) => (
            <div
              key={incident.id}
              className={`incident-card ${(incident.severity || "low").toLowerCase()}`}
              onClick={() => setSelectedIncident(incident)}
            >
              <div className="incident-header">
                <span className={`badge ${(incident.severity || "low").toLowerCase()}`}>
                  {incident.severity}
                </span>

                <small>
                  {incident.time
                    ? new Date(incident.time).toLocaleString()
                    : "Unknown Time"}
                </small>
              </div>

              <h3>{incident.alert_type}</h3>

              <p>
                <strong>Device:</strong> {incident.device}
              </p>

              <p>
                <strong>Status:</strong> {incident.status}
              </p>
            </div>
          ))
        )}
      </div>

      {selectedIncident && (
        <div className="drawer-overlay" onClick={() => setSelectedIncident(null)}>
          <div className="incident-drawer" onClick={(e) => e.stopPropagation()}>
            <button
              className="drawer-close"
              onClick={() => setSelectedIncident(null)}
            >
              ×
            </button>

            <h2>Incident #{selectedIncident.id}</h2>

            <span
              className={`badge ${(selectedIncident.severity || "low").toLowerCase()}`}
            >
              {selectedIncident.severity}
            </span>

            <div className="drawer-section">
              <h3>Summary</h3>
              <p>{selectedIncident.message}</p>
            </div>

            <div className="drawer-section">
              <h3>Affected Asset</h3>
              <p>
                <strong>Device:</strong> {selectedIncident.device}
              </p>
              <p>
                <strong>Alert Type:</strong> {selectedIncident.alert_type}
              </p>
              <p>
                <strong>Status:</strong> {selectedIncident.status}
              </p>
              <p>
                <strong>Acknowledged:</strong>{" "}
                {selectedIncident.acknowledged ? "Yes" : "No"}
              </p>
            </div>

            <div className="drawer-section">
              <h3>MITRE ATT&CK for ICS</h3>
              <p>{selectedIncident.mitre_technique || "Unmapped"}</p>
            </div>

            <div className="drawer-section">
              <h3>Recommended Actions</h3>
              <ul>
                <li>Validate the affected asset status with operations.</li>
                <li>Review recent authentication and engineering workstation activity.</li>
                <li>Compare firmware/configuration against the approved baseline.</li>
                <li>Confirm network segmentation and firewall rules.</li>
                <li>Document findings and preserve relevant logs.</li>
              </ul>
            </div>

            <div className="drawer-section">
              <h3>Timeline</h3>
              <p>
                <strong>Detected:</strong>{" "}
                {selectedIncident.time
                  ? new Date(selectedIncident.time).toLocaleString()
                  : "Unknown"}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default IncidentCenter;