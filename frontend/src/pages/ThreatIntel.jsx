function ThreatIntel({ threatLevel, alerts, incidents, vulnerabilities }) {
  const criticalAlerts = (alerts || []).filter(
    (a) => a.severity === "Critical"
  ).length;

  const openIncidents = (incidents || []).filter(
    (i) => i.status !== "Closed"
  ).length;

  const openFindings = (vulnerabilities || []).filter(
    (v) => v.status === "Open"
  ).length;

  return (
    <>
      <section className="threat-intel-page">
        <div className="threat-intel-header">
          <div>
            <h2>Threat Intelligence Center</h2>
            <p>
              Simulated rail OT threat intelligence, MITRE ATT&CK for ICS
              coverage, and advisory tracking.
            </p>
          </div>

          <div className={`threat-pill ${threatLevel.toLowerCase()}`}>
            {threatLevel}
          </div>
        </div>

        <div className="threat-intel-grid">

                  <div className="intel-card mitre-coverage">
                      <h3>MITRE ATT&CK Coverage</h3>

                      <div className="mitre-row">
                          <span>Discovery</span>
                          <div className="mitre-bar"><div style={{ width: "75%" }}></div></div>
                      </div>

                      <div className="mitre-row">
                          <span>Execution</span>
                          <div className="mitre-bar"><div style={{ width: "55%" }}></div></div>
                      </div>

                      <div className="mitre-row">
                          <span>Persistence</span>
                          <div className="mitre-bar"><div style={{ width: "35%" }}></div></div>
                      </div>

                      <div className="mitre-row">
                          <span>Impact</span>
                          <div className="mitre-bar"><div style={{ width: "65%" }}></div></div>
                      </div>
                  </div> 
          <div className="intel-card">
            <h3>Current Threat Posture</h3>
            <p><strong>Critical Alerts:</strong> {criticalAlerts}</p>
            <p><strong>Open Incidents:</strong> {openIncidents}</p>
            <p><strong>Open Findings:</strong> {openFindings}</p>
          </div>

          <div className="intel-card">
            <h3>MITRE ATT&CK for ICS</h3>
            <ul>
              <li>T0842 - Network Service Scanning</li>
              <li>T0859 - Modify Controller Tasking</li>
              <li>T0881 - Service Stop</li>
              <li>T0812 - Default Credentials / Valid Accounts</li>
            </ul>
          </div>

          <div className="intel-card">
            <h3>Simulated IOC Feed</h3>
            <ul>
              <li>203.0.113.45 - Suspicious OT scan source</li>
              <li>ptc-update-check.example - Suspicious domain</li>
              <li>rail-maint-tool.exe - Unknown engineering utility</li>
              <li>SHA256: DEMO-IOC-RAIL-0001</li>
            </ul>
          </div>

          <div className="intel-card">
            <h3>Vendor Advisory Watch</h3>
            <ul>
              <li>Siemens rail automation firmware review</li>
              <li>Wabtec crossing controller patch validation</li>
              <li>Meteorcomm communications gateway monitoring</li>
              <li>Microsoft engineering workstation hardening</li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}

export default ThreatIntel;