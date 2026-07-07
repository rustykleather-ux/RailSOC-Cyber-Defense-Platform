function ExecutiveDashboard({
  dashboard,
  alerts,
  incidents,
  vulnerabilities,
  threatLevel,
}) {
  const criticalAlerts = (alerts || []).filter((a) => a.severity === "Critical").length;
  const highAlerts = (alerts || []).filter((a) => a.severity === "High").length;
  const openIncidents = (incidents || []).filter((i) => i.status !== "Closed").length;
  const offlineAssets = dashboard?.offline_devices || 0;
  const highRiskAssets = dashboard?.high_risk_devices || 0;
  const openVulnerabilities = (vulnerabilities || []).filter((v) => v.status === "Open").length;

  const securityScore = Math.max(
    0,
    100 -
      criticalAlerts * 15 -
      highAlerts * 8 -
      openIncidents * 10 -
      offlineAssets * 5 -
      openVulnerabilities * 2
  );

  const totalAssets = dashboard?.total_devices || 0;
  const onlineAssets = dashboard?.online_devices || 0;
  const protectedAssets =
    totalAssets > 0 ? Math.round((onlineAssets / totalAssets) * 100) : 100;

  const recommendations = [];

  if (criticalAlerts > 0) recommendations.push("Investigate critical Rail OT alerts immediately.");
  if (openIncidents > 0) recommendations.push("Review open incidents and confirm analyst ownership.");
  if (offlineAssets > 0) recommendations.push("Restore communications to offline railroad OT assets.");
  if (highRiskAssets > 0) recommendations.push("Prioritize high-risk signal, PTC, or dispatch systems.");
  if (openVulnerabilities > 0) recommendations.push("Schedule controlled remediation for open vulnerability findings.");

  if (recommendations.length === 0) {
    recommendations.push("Maintain current monitoring posture and continue baseline validation.");
  }

  return (
    <section className="executive-page">
      <div className="executive-header">
        <div>
          <h2>Executive Security Operations Dashboard</h2>
          <p>
            Leadership-level summary of TrackSentinel railroad OT security posture.
          </p>
        </div>
              <button className="export-button" onClick={() => window.print()}>
                  Export PDF
              </button>
        <span className={`threat-pill ${threatLevel.toLowerCase()}`}>
          {threatLevel}
        </span>
      </div>

      <div className="executive-hero">
        <div className="score-card">
          <span>Overall Security Score</span>
          <strong>{securityScore}%</strong>
          <small>Calculated from alerts, incidents, assets, and vulnerabilities</small>
        </div>

        <div className="kpi-card">
          <span>MTTD</span>
          <strong>1m 42s</strong>
          <small>Mean time to detect</small>
        </div>

        <div className="kpi-card">
          <span>MTTR</span>
          <strong>7m 31s</strong>
          <small>Mean time to respond</small>
        </div>

        <div className="kpi-card">
          <span>Protected Assets</span>
          <strong>{protectedAssets}%</strong>
          <small>{onlineAssets} of {totalAssets} operational</small>
        </div>
      </div>

      <div className="executive-grid">
        <div className="executive-panel">
          <h3>Security KPIs</h3>

          <div className="exec-metric-row">
            <span>Open Incidents</span>
            <strong>{openIncidents}</strong>
          </div>

          <div className="exec-metric-row">
            <span>Critical Alerts</span>
            <strong>{criticalAlerts}</strong>
          </div>

          <div className="exec-metric-row">
            <span>High Risk Assets</span>
            <strong>{highRiskAssets}</strong>
          </div>

          <div className="exec-metric-row">
            <span>Open Vulnerabilities</span>
            <strong>{openVulnerabilities}</strong>
          </div>
        </div>

        <div className="executive-panel">
          <h3>Compliance Posture</h3>

          <div className="compliance-row">
            <span>NIST CSF</span>
            <div className="compliance-bar"><div style={{ width: "95%" }}></div></div>
            <strong>95%</strong>
          </div>

          <div className="compliance-row">
            <span>IEC 62443</span>
            <div className="compliance-bar"><div style={{ width: "90%" }}></div></div>
            <strong>90%</strong>
          </div>

          <div className="compliance-row">
            <span>NERC CIP</span>
            <div className="compliance-bar"><div style={{ width: "92%" }}></div></div>
            <strong>92%</strong>
          </div>

          <div className="compliance-row">
            <span>CIS Controls</span>
            <div className="compliance-bar"><div style={{ width: "89%" }}></div></div>
            <strong>89%</strong>
          </div>
        </div>

        <div className="executive-panel wide">
          <h3>Executive Recommendations</h3>

          <ul className="recommendation-list">
            {recommendations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export default ExecutiveDashboard;