function Roadmap() {
  const completed = [
    "Railroad OT Asset Inventory",
    "Environment Overview",
    "Live Asset Telemetry",
    "Railroad Network Topology",
    "Security Alerts",
    "Incident Center",
    "Attack Simulation Engine",
    "Vulnerability Management",
    "MITRE ATT&CK for ICS Mapping",
  ];

  const planned = [
    "Executive Reporting Dashboard",
    "Interactive Railroad Map",
    "Digital Twin Visualization",
    "Threat Intelligence Feed",
    "Purple Team Exercise Library",
    "Role-Based Access Control",
    "Asset Configuration History",
    "Syslog / SIEM Integration",
  ];

  return (
    <section className="roadmap-section" id="reports">
      <div className="roadmap-card">
        <h2>Platform Roadmap</h2>
        <p>
          TrackSentinel is an actively developed portfolio project focused on
          railroad OT cybersecurity operations.
        </p>

        <div className="roadmap-grid">
          <div>
            <h3>✅ Current Capabilities</h3>

            <ul>
              {completed.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div id="settings">
            <h3>🚀 Planned Enhancements</h3>

            <ul>
              {planned.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

export default Roadmap;