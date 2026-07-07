function EnvironmentOverview({ dashboard, alerts, incidents, vulnerabilities }) {
  if (!dashboard) return null;

  const activeAlerts = alerts?.length || 0;
  const openIncidents = incidents?.length || 0;
  const openVulnerabilities =
    dashboard.open_vulnerabilities ?? vulnerabilities?.length ?? 0;

  const offlineAssets = dashboard.offline_devices || 0;
  const highRiskAssets = dashboard.high_risk_devices || 0;

  const threatLevel =
    dashboard.critical_alerts > 0 || highRiskAssets > 0
      ? "Elevated"
      : activeAlerts > 0 || offlineAssets > 0
      ? "Guarded"
      : "Normal";

  const platformStatus =
    threatLevel === "Normal" ? "Operational" : "Attention Required";

  return (
    <section className="environment-overview">
      <div className="overview-header">
        <div>
          <h2>Environment Overview</h2>
          <p>
            Real-time summary of the simulated railroad OT security environment.
          </p>
        </div>

        <div className={`overview-status ${threatLevel.toLowerCase()}`}>
          <span className="pulse-dot"></span>
          {platformStatus}
        </div>
      </div>

      <div className="overview-grid">
        <div className="overview-card">
          <span>OT Assets</span>
          <strong>{dashboard.total_devices}</strong>
          <small>{dashboard.online_devices} operational</small>
        </div>

        <div className="overview-card warning">
          <span>Active Alerts</span>
          <strong>{activeAlerts}</strong>
          <small>{dashboard.critical_alerts || 0} critical</small>
        </div>

        <div className="overview-card danger">
          <span>Open Incidents</span>
          <strong>{openIncidents}</strong>
          <small>Analyst workflow active</small>
        </div>

        <div className="overview-card">
          <span>Operational Assets</span>
          <strong>{dashboard.online_devices}</strong>
          <small>{offlineAssets} offline</small>
        </div>

        <div className="overview-card danger">
          <span>High Risk Assets</span>
          <strong>{highRiskAssets}</strong>
          <small>Critical infrastructure risk</small>
        </div>

        <div className="overview-card warning">
          <span>Open Findings</span>
          <strong>{openVulnerabilities}</strong>
          <small>Vulnerability queue</small>
        </div>

        <div className="overview-card">
          <span>Simulation Mode</span>
          <strong>Enabled</strong>
          <small>Training environment</small>
        </div>

        <div className={`overview-card threat ${threatLevel.toLowerCase()}`}>
          <span>Threat Level</span>
          <strong>{threatLevel}</strong>
          <small>RailSOC posture</small>
        </div>
      </div>
    </section>
  );
}

export default EnvironmentOverview;