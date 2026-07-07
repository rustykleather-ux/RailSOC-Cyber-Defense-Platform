import Roadmap from "../components/Roadmap";

function Reports({ dashboard, alerts, incidents, vulnerabilities, threatLevel }) {
  const totalAssets = dashboard?.total_devices || 0;
  const onlineAssets = dashboard?.online_devices || 0;
  const offlineAssets = dashboard?.offline_devices || 0;
  const highRiskAssets = dashboard?.high_risk_devices || 0;

  const openAlerts = (alerts || []).filter((a) => a.status !== "Closed").length;
  const criticalAlerts = (alerts || []).filter(
    (a) => a.severity === "Critical"
  ).length;

  const openIncidents = (incidents || []).filter(
    (i) => i.status !== "Closed"
  ).length;

  const openVulnerabilities = (vulnerabilities || []).filter(
    (v) => v.status === "Open"
  ).length;

  return (
    <>
      <section className="report-page">
        <div className="report-header">
          <div>
            <h2>Executive Reports</h2>
            <p>
              Current RailSOC summary for the simulated TrackSentinel railroad
              OT environment.
            </p>
          </div>

          <span className={`threat-pill ${threatLevel.toLowerCase()}`}>
            {threatLevel}
          </span>
        </div>

        <div className="report-grid">
          <div className="report-card">
            <span>Assets</span>
            <strong>{totalAssets}</strong>
            <small>{onlineAssets} operational · {offlineAssets} offline</small>
          </div>

          <div className="report-card warning">
            <span>Alerts</span>
            <strong>{openAlerts}</strong>
            <small>{criticalAlerts} critical</small>
          </div>

          <div className="report-card danger">
            <span>Incidents</span>
            <strong>{openIncidents}</strong>
            <small>Active analyst workflow</small>
          </div>

          <div className="report-card">
            <span>High Risk Assets</span>
            <strong>{highRiskAssets}</strong>
            <small>Priority OT systems</small>
          </div>

          <div className="report-card warning">
            <span>Vulnerabilities</span>
            <strong>{openVulnerabilities}</strong>
            <small>Open security findings</small>
          </div>

          <div className="report-card">
            <span>Threat Posture</span>
            <strong>{threatLevel}</strong>
            <small>Current RailSOC state</small>
          </div>
        </div>

        <div className="report-section">
          <h3>Executive Summary</h3>
          <p>
            TrackSentinel is currently operating in <strong>{threatLevel}</strong>{" "}
            posture. The simulated environment contains {totalAssets} railroad OT
            assets, {openAlerts} active alerts, {openIncidents} open incidents,
            and {openVulnerabilities} open vulnerability findings.
          </p>
        </div>

        <div className="report-section">
          <h3>Recommended Focus</h3>
          <ul>
            <li>Review critical and high severity incidents first.</li>
            <li>Validate the status of offline or high-risk OT assets.</li>
            <li>Prioritize vulnerabilities affecting safety-critical systems.</li>
            <li>Document investigation notes and analyst actions.</li>
          </ul>
        </div>
      </section>

      <Roadmap />
    </>
  );
}

export default Reports;