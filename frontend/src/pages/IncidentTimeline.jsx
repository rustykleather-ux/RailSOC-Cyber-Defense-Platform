function IncidentTimeline({ incidents }) {
  const timelineItems = (incidents || [])
    .slice()
    .sort((a, b) => new Date(b.time) - new Date(a.time));

  return (
    <section className="timeline-page">
      <div className="timeline-header">
        <h2>Incident Timeline</h2>
        <p>
          Chronological view of simulated RailSOC security events and analyst workflow.
        </p>
      </div>

      <div className="timeline-list">
        {timelineItems.length === 0 ? (
          <div className="timeline-empty">No incident activity recorded.</div>
        ) : (
          timelineItems.map((incident) => (
            <div className="timeline-item" key={incident.id}>
              <div className={`timeline-dot ${(incident.severity || "low").toLowerCase()}`}></div>

              <div className="timeline-content">
                <div className="timeline-meta">
                  <span className={`badge ${(incident.severity || "low").toLowerCase()}`}>
                    {incident.severity || "Unknown"}
                  </span>

                  <small>
                    {incident.time
                      ? new Date(incident.time).toLocaleString()
                      : "Unknown Time"}
                  </small>
                </div>

                <h3>{incident.alert_type || "Rail OT Incident"}</h3>

                <p>{incident.message || "No incident summary available."}</p>

                <div className="timeline-details">
                  <span><strong>Asset:</strong> {incident.device || "Unknown"}</span>
                  <span><strong>Status:</strong> {incident.status || "Unknown"}</span>
                  <span><strong>Assigned:</strong> {incident.assigned_to || "Unassigned"}</span>
                  <span><strong>MITRE:</strong> {incident.mitre_technique || "Unmapped"}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

export default IncidentTimeline;