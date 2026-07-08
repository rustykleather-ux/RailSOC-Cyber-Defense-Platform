function InvestigationWorkspace({ incidents }) {
  const activeIncident =
    (incidents || []).find((i) => i.status !== "Closed") || null;

  if (!activeIncident) {
    return (
      <section className="investigation-page">
        <h2>Investigation Workspace</h2>
        <p className="muted">
          No active investigations. Launch a simulation from the Training page
          to begin an investigation.
        </p>
      </section>
    );
  }

const timelineEvents = [
  {
    time: "08:14",
    title: "Initial Detection",
    detail: activeIncident.alert_type,
    type: "Detection",
  },
  {
    time: "08:16",
    title: "Asset Impact Identified",
    detail: activeIncident.device,
    type: "Asset",
  },
  {
    time: "08:18",
    title: "MITRE Technique Mapped",
    detail: activeIncident.mitre_technique || "Unmapped",
    type: "MITRE",
  },
  {
    time: "08:21",
    title: "Incident Created",
    detail: activeIncident.message,
    type: "Incident",
  },
  {
    time: "08:24",
    title: "Analyst Workflow",
    detail: activeIncident.assigned_to || "Awaiting analyst assignment",
    type: "Response",
  },
];
    
  return (
    <section className="investigation-page">
      <div className="investigation-header">
        <div>
          <h2>Investigation Workspace</h2>
          <p>
            RailSOC Analyst Investigation Console
          </p>
        </div>

        <span className={`badge ${(activeIncident.severity || "low").toLowerCase()}`}>
          {activeIncident.severity}
        </span>
      </div>

      <div className="investigation-grid">
              <div className="investigation-card wide">
                  <h3>Investigation Timeline</h3>

                  <div className="investigation-timeline">
                      {timelineEvents.map((event, index) => (
                          <div className="investigation-timeline-item" key={index}>
                              <div className="timeline-time">{event.time}</div>

                              <div className="timeline-marker"></div>

                              <div className="timeline-event-card">
                                  <span>{event.type}</span>
                                  <strong>{event.title}</strong>
                                  <p>{event.detail}</p>
                              </div>
                          </div>
                      ))}
                  </div>
              </div>
        <div className="investigation-card">
          <h3>Incident Summary</h3>

          <p><strong>ID:</strong> #{activeIncident.id}</p>
          <p><strong>Type:</strong> {activeIncident.alert_type}</p>
          <p><strong>Asset:</strong> {activeIncident.device}</p>
          <p><strong>Status:</strong> {activeIncident.status}</p>
          <p><strong>Assigned:</strong> {activeIncident.assigned_to || "Unassigned"}</p>
        </div>

              <div className="investigation-card">
                  <h3>Analyst Actions</h3>

                  <p className="muted">
                      Continue investigation using the full incident management workflow.
                  </p>

                  <a className="investigation-link-button" href="/incidents">
                      Open Incident Center
                  </a>

                  <a className="investigation-link-button secondary" href="/timeline">
                      View Incident Timeline
                  </a>
              </div>

        <div className="investigation-card">
          <h3>MITRE ATT&CK</h3>

          <p>{activeIncident.mitre_technique || "Unmapped"}</p>

          <h4>Analyst Guidance</h4>

          <ul>
            <li>Validate asset state</li>
            <li>Review engineering changes</li>
            <li>Collect authentication logs</li>
            <li>Review firewall activity</li>
            <li>Preserve forensic evidence</li>
          </ul>
        </div>
        
        
        <div className="investigation-card wide">
          <h3>Evidence</h3>

          <table>
            <tbody>
              <tr>
                <td>Asset</td>
                <td>{activeIncident.device}</td>
              </tr>

              <tr>
                <td>Detection Time</td>
                <td>{new Date(activeIncident.time).toLocaleString()}</td>
              </tr>

              <tr>
                <td>Alert</td>
                <td>{activeIncident.alert_type}</td>
              </tr>

              <tr>
                <td>Current Status</td>
                <td>{activeIncident.status}</td>
              </tr>

              <tr>
                <td>Evidence</td>
                <td>Simulation Evidence Collected</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="investigation-card wide">
          <h3>IOC Summary</h3>

          <ul>
            <li>192.168.50.10</li>
            <li>{activeIncident.device}</li>
            <li>{activeIncident.alert_type}</li>
            <li>{activeIncident.mitre_technique}</li>
          </ul>
        </div>

      </div>
    </section>
  );
}

export default InvestigationWorkspace;