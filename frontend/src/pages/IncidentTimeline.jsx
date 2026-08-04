function IncidentTimeline({ incidents, events = [] }) {
  const operationalItems = (events || []).map((event) => ({
    ...event,
    time: event.timestamp,
    alert_type: event.title,
    device: event.asset_name,
    status: event.event_type,
  }));
  const timelineItems = (
    operationalItems.length > 0 ? operationalItems : incidents || []
  )
    .slice()
    .sort((a, b) => new Date(b.time) - new Date(a.time));

  return (
    <section className="timeline-page">
      <div className="timeline-header">
        <h2>Incident Timeline</h2>
        <p>
          Latest-first view of simulated RailSOC security events and analyst workflow.
        </p>
      </div>

      <div className="timeline-list">
        {timelineItems.length === 0 ? (
          <div className="timeline-empty">No incident activity recorded.</div>
        ) : (
          timelineItems.map((incident) => (
            <div
              className={`timeline-item timeline-item--${
                String(incident.event_type || "incident").split("_")[0]
              }`}
              key={`${incident.event_type || "incident"}-${incident.id}`}
            >
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

                <h3>{incident.title || incident.alert_type || "Rail OT Incident"}</h3>

                <p>{incident.message || incident.description || "No incident summary available."}</p>

                <div className="timeline-details">
                  <span><strong>Asset:</strong> {incident.device || "Unknown"}</span>
                  <span><strong>Status:</strong> {incident.status || "Unknown"}</span>
                  {incident.incident_id && (
                    <span><strong>Incident:</strong> {incident.incident_id}</span>
                  )}
                  {incident.train_id && (
                    <span><strong>Train ID:</strong> {incident.train_id}</span>
                  )}
                  {incident.track_block_id && (
                    <span><strong>Block ID:</strong> {incident.track_block_id}</span>
                  )}
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
